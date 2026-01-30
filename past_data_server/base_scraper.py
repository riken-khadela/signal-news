"""
Base Scraper Class for News Scrapers
=====================================
Provides common functionality for all news scrapers:
- Configuration management
- Skip threshold logic
- Early termination (run_loop)
- Incremental scraping support
- Standardized logging

All scrapers should inherit from this class and implement:
- get_grid_details() - Fetch article listings
- scrape_grid_data() - Parse article data from HTML
- parse_blog_details() - Extract full article content
- run() - Main execution logic

Author: AI Assistant
Date: 2026-01-28
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import pytz
from logger import CustomLogger

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

class BaseScraper:
    """Base class for all news scrapers with common functionality"""
    
    def __init__(self, db_client, log_folder: str = "log/scrapers"):
        """
        Initialize base scraper
        
        Args:
            db_client: MongoDB collection client for this scraper
            log_folder: Path to log folder
        """
        self.db_client = db_client
        self.logger = CustomLogger(log_folder=log_folder)
        
        # Default configuration
        self.config = {
            'max_pages': 5,
            'skip_threshold': 10,
            'enable_skip_logic': True,
            'mode': 'incremental'
        }
        
        # State tracking
        self.page_index = 1
        self.run_loop = True
        self.skipped_urls = 0
        self.consecutive_skips = 0
        self.total_articles_scraped = 0
        
        # Adaptive page indexing state (for full mode)
        self.skip_stage = 0  # 0=+1, 1=+5, 2=+10, 3=+20
        self.skipped_pages = []  # Pages that were skipped during fast indexing
        self.last_empty_page = None  # Last page where grid_details was empty
        self.articles_saved_this_page = 0  # Track articles saved in current page
        
        # Timezone
        self.ist = pytz.timezone("Asia/Kolkata")
        self.utc = pytz.UTC
    
    def set_config(self, config: Dict):
        """
        Set configuration from z_main.py
        
        Args:
            config: Configuration dictionary with keys:
                - max_pages: Maximum pages to scrape
                - skip_threshold: Stop after N consecutive skips
                - enable_skip_logic: Enable early termination
                - mode: 'full' or 'incremental'
        """
        self.config.update(config)
        self.logger.info(f"📝 Configuration updated: {self.config}")
    
    def should_continue_scraping(self) -> bool:
        """
        Check if scraping should continue based on:
        - run_loop flag
        - Page limit (in incremental mode)
        - Skip threshold
        
        Returns:
            bool: True if should continue, False otherwise
        """
        # Check run_loop flag
        if not self.run_loop:
            self.logger.info("⏹️  run_loop=False, stopping scraper")
            return False
        
        # Check page limit in incremental mode
        if self.config['mode'] == 'incremental':
            max_pages = self.config.get('max_pages', 5)
            if self.page_index > max_pages:
                self.logger.info(f"⏹️  Reached page limit ({max_pages}), stopping scraper")
                return False
        
        # Check skip threshold
        print(self.config['mode'])
        if self.config['mode'] == 'incremental':
            if self.config.get('enable_skip_logic', True):
                skip_threshold = self.config.get('skip_threshold', 10)
                if self.consecutive_skips >= skip_threshold:
                    self.logger.warning(
                        f"⏹️  Reached skip threshold ({skip_threshold} consecutive skips), stopping scraper"
                    )
                    return False
        
        return True
    
    def should_break_loop(self, page_index : int = 0, previous_grid : list = [], grid_details : list = []):
        if self.config['mode'] == 'full':
            if page_index >= 5000:
                return True
        else :
            if previous_grid == grid_details:
                return True
            return False

    def get_new_page_index(self, page_index, grid_details: list) -> int:
        """
        Adaptive page indexing for efficient scraping.
        
        In 'full' mode:
        - If articles were saved: Normal +1 increment (productive page)
        - If NO articles saved (all existing or empty): Progressive skip (1→5→10→20)
        - Tracks skipped pages for backtracking when new articles are found
        
        Args:
            page_index: Current page index
            grid_details: List of articles found on current page
            
        Returns:
            int: Next page index to scrape
        """
        if self.config['mode'] == 'full':
            # Check if this page was productive (saved new articles)
            was_productive = self.articles_saved_this_page > 0
            
            # Reset counter for next page
            self.articles_saved_this_page = 0
            
            if not was_productive:
                # No new articles saved - apply adaptive skipping
                self.last_empty_page = page_index
                
                skip_increments = [1, 5, 10, 20]
                current_increment = skip_increments[min(self.skip_stage, 3)]
                
                next_page = page_index + current_increment
                
                if current_increment > 1:
                    skipped = list(range(page_index + 1, next_page))
                    self.skipped_pages.extend(skipped)
                    self.logger.info(f"🚀 Fast-forward: Stage {self.skip_stage} (+{current_increment}) - No new articles saved, skipping pages {skipped}")
                
                if self.skip_stage < 3:
                    self.skip_stage += 1
                
                return next_page
            else:
                # Articles were saved! This is a productive page
                if self.last_empty_page is not None and self.skipped_pages:
                    # We were skipping pages but now found new content
                    self.logger.warning(f"⚠️ New articles saved after unproductive pages! Backtracking to scrape {len(self.skipped_pages)} skipped pages")
                    
                    next_page = self.skipped_pages.pop(0)
                    
                    self.skip_stage = 0
                    self.last_empty_page = None
                    
                    self.logger.info(f"↩️ Backtracking to page {next_page}")
                    return next_page
                else:
                    # Normal progression - reset skip stage
                    self.skip_stage = 0
                    self.last_empty_page = None
                    return page_index + 1
        else:
            # Incremental mode - simple increment
            self.articles_saved_this_page = 0
            return page_index + 1
        
        return page_index + 1

    def check_article_exists(self, url: str) -> bool:
        """
        Check if article already exists in database
        
        Args:
            url: Article URL to check
            
        Returns:
            bool: True if exists, False otherwise
        """
        try:
            exists = self.db_client.find_one({"url": url}) is not None
            if exists:
                if not self.config['mode'] == "full" :
                    self.consecutive_skips += 1
                    self.skipped_urls += 1
            else:
                self.consecutive_skips = 0  # Reset on new article
            
            return exists
        except Exception as e:
            self.logger.error(f"❌ Error checking article existence: {e}")
            return False
    
    def is_article_too_old(self, article_date: datetime, cutoff_year: int = 2025) -> bool:
        """
        Check if article is older than cutoff date (Jan 1, cutoff_year)
        
        Args:
            article_date: Article publication date
            cutoff_year: Year to use as cutoff (default: 2025)
            
        Returns:
            bool: True if too old, False otherwise
        """
        try:
            cutoff_date = datetime(cutoff_year, 1, 1, tzinfo=timezone.utc)
            
            # Ensure article_date is timezone-aware
            if article_date.tzinfo is None:
                article_date = article_date.replace(tzinfo=timezone.utc)
            
            is_old = article_date < cutoff_date
            
            if is_old:
                self.logger.info(f"⏭️  Article too old: {article_date} < {cutoff_date}")
                self.run_loop = False  # Stop scraping old articles
            
            return is_old
        except Exception as e:
            self.logger.error(f"❌ Error checking article date: {e}")
            return False
    
    def fix_data_doc(self,data_doc):
        """
        Ensures all required keys exist in the data_doc dictionary.
        If any key is missing, it will be added with default values.
        
        Args:
            data_doc (dict): The input dictionary to validate and fix
            
        Returns:
            dict: A properly structured data_doc with all required keys
        """
        # Define the template structure
        template = {
            "author": "",
            "image": "",
            "url": "",
            "title": "",
            "time": "",
            "description": {
                "summary": "",
                "details": ""
            }
        }
        
        # Create a fixed data_doc starting with the template
        fixed_doc = {}
        
        # Check and add top-level keys
        for key in ["author", "image", "url", "title", "time"]:
            fixed_doc[key] = data_doc.get(key, template[key])
        
        # Handle the nested 'description' key
        if "description" in data_doc and isinstance(data_doc["description"], dict):
            fixed_doc["description"] = {
                "summary": data_doc["description"].get("summary", ""),
                "details": data_doc["description"].get("details", "")
            }
        else:
            fixed_doc["description"] = template["description"].copy()
        
        fixed_doc['created_at'] = ist_time
        return fixed_doc
    
    def save_article(self, article_data: Dict) -> bool:
        """
        Save article to database with upsert
        
        Args:
            article_data: Article data dictionary
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Check if article exists first (if skip_existing is enabled)
            if self.config.get('skip_existing', True):
                if self.check_article_exists(article_data.get('url', '')):
                    return False
            
            # Upsert article
            self.db_client.update_one(
                {"url": article_data['url']},
                {"$set": self.fix_data_doc(article_data)},
                upsert=True
            )
            
            self.total_articles_scraped += 1
            self.articles_saved_this_page += 1  # Track for adaptive indexing
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error saving article: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Get scraping statistics
        
        Returns:
            dict: Statistics dictionary
        """
        return {
            'total_articles_scraped': self.total_articles_scraped,
            'skipped_urls': self.skipped_urls,
            'consecutive_skips': self.consecutive_skips,
            'pages_scraped': self.page_index - 1,
            'stopped_early': not self.run_loop
        }
    
    def log_stats(self):
        """Log final scraping statistics"""
        stats = self.get_stats()
        self.logger.info("=" * 60)
        self.logger.info("📊 SCRAPING STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"✅ Articles Scraped: {stats['total_articles_scraped']}")
        self.logger.info(f"⏭️  Articles Skipped: {stats['skipped_urls']}")
        self.logger.info(f"📄 Pages Processed: {stats['pages_scraped']}")
        self.logger.info(f"⏹️  Early Termination: {stats['stopped_early']}")
        self.logger.info("=" * 60)
    
    # Abstract methods to be implemented by subclasses
    def get_grid_details(self):
        """Fetch article listings - to be implemented by subclass"""
        raise NotImplementedError("Subclass must implement get_grid_details()")
    
    def scrape_grid_data(self, html_content):
        """Parse article data from HTML - to be implemented by subclass"""
        raise NotImplementedError("Subclass must implement scrape_grid_data()")
    
    def parse_blog_details(self, url):
        """Extract full article content - to be implemented by subclass"""
        raise NotImplementedError("Subclass must implement parse_blog_details()")
    
    def run(self):
        """Main execution logic - to be implemented by subclass"""
        raise NotImplementedError("Subclass must implement run()")
