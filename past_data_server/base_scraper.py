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
        if self.config.get('enable_skip_logic', True):
            skip_threshold = self.config.get('skip_threshold', 10)
            if self.consecutive_skips >= skip_threshold:
                self.logger.warning(
                    f"⏹️  Reached skip threshold ({skip_threshold} consecutive skips), stopping scraper"
                )
                return False
        
        return True
    
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
                {"$set": article_data},
                upsert=True
            )
            
            self.total_articles_scraped += 1
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
