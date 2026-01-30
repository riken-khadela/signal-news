from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import pytz
from logger import CustomLogger

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

class BaseScraper:
    
    def __init__(self, db_client, log_folder: str = "log/scrapers"):
        
        self.db_client = db_client
        self.logger = CustomLogger(log_folder=log_folder)
        self.config = {
            'max_pages': 5,
            'skip_threshold': 10,
            'enable_skip_logic': True,
            'mode': 'incremental'
        }
        self.page_index = 1
        self.run_loop = True
        self.skipped_urls = 0
        self.consecutive_skips = 0
        self.total_articles_scraped = 0
        self.skip_stage = 0  
        self.skipped_pages = []  
        self.last_empty_page = None  
        self.articles_saved_this_page = 0
        self.is_in_backtrack_mode = False  # Explicit backtracking flag   
        self.ist = pytz.timezone("Asia/Kolkata")
        self.utc = pytz.UTC
    
    def set_config(self, config: Dict):
        
        self.config.update(config)
        self.logger.info(f"📝 Configuration updated: {self.config}")
    
    def should_continue_scraping(self) -> bool:
        
        if not self.run_loop:
            self.logger.info("⏹️  run_loop=False, stopping scraper")
            return False
        
        if self.config['mode'] == 'incremental':
            max_pages = self.config.get('max_pages', 5)
            if self.page_index > max_pages:
                self.logger.info(f"⏹️  Reached page limit ({max_pages}), stopping scraper")
                return False
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
        Adaptive page indexing with smart backtracking.
        
        Forward mode: Skip 1→5→10→20 when no articles saved
        Backtrack mode: Process skipped pages sequentially when articles found
        """
        if self.config['mode'] != 'full':
            # Incremental mode - simple +1
            self.articles_saved_this_page = 0
            return page_index + 1
        
        # Check productivity
        was_productive = self.articles_saved_this_page > 0
        saved_count = self.articles_saved_this_page
        self.articles_saved_this_page = 0  # Reset for next page
        
        # === BACKTRACKING MODE ===
        if self.is_in_backtrack_mode:
            if self.skipped_pages:
                # Continue processing skipped pages
                next_page = self.skipped_pages.pop(0)
                if was_productive:
                    self.logger.info(f"↩️ Backtracking to page {next_page} (saved {saved_count} articles on page {page_index})")
                else:
                    self.logger.info(f"↩️ Backtracking to page {next_page}")
                return next_page
            else:
                # Finished backtracking
                self.logger.info(f"✅ Backtracking complete! Resuming from page {page_index + 1}")
                self.is_in_backtrack_mode = False
                self.skip_stage = 0
                self.last_empty_page = None
                return page_index + 1
        
        # === FORWARD MODE ===
        if was_productive:
            # Articles saved - check if we need to start backtracking
            if self.skipped_pages:
                # We have skipped pages and just found articles - START BACKTRACKING
                self.is_in_backtrack_mode = True
                next_page = self.skipped_pages.pop(0)
                self.logger.warning(f"⚠️ Found {saved_count} articles! Starting backtrack through {len(self.skipped_pages) + 1} skipped pages")
                self.logger.info(f"↩️ Backtracking to page {next_page}")
                return next_page
            else:
                # Normal progression - no skipped pages
                self.skip_stage = 0
                self.last_empty_page = None
                return page_index + 1
        else:
            # No articles saved - apply adaptive skipping
            self.last_empty_page = page_index
            
            skip_increments = [1, 5, 10, 20]
            current_increment = skip_increments[min(self.skip_stage, 3)]
            
            next_page = page_index + current_increment
            
            if current_increment > 1:
                # Create NEW skip list (replaces old one)
                skipped = list(range(page_index + 1, next_page))
                self.skipped_pages = skipped
                self.logger.info(f"🚀 Fast-forward: Stage {self.skip_stage} (+{current_increment}) - Skipping to page {next_page}")
            else:
                # Stage 0 (+1) - no skipping
                self.skipped_pages = []
            
            if self.skip_stage < 3:
                self.skip_stage += 1
            
            return next_page

    def check_article_exists(self, url: str) -> bool:
        
        try:
            exists = self.db_client.find_one({"url": url}) is not None
            if exists:
                if not self.config['mode'] == "full" :
                    self.consecutive_skips += 1
                    self.skipped_urls += 1
            else:
                self.consecutive_skips = 0
            
            return exists
        except Exception as e:
            self.logger.error(f"❌ Error checking article existence: {e}")
            return False
    
    def is_article_too_old(self, article_date: datetime, cutoff_year: int = 2025) -> bool:
        
        try:
            cutoff_date = datetime(cutoff_year, 1, 1, tzinfo=timezone.utc)
            
            
            if article_date.tzinfo is None:
                article_date = article_date.replace(tzinfo=timezone.utc)
            
            is_old = article_date < cutoff_date
            
            if is_old:
                self.logger.info(f"⏭️  Article too old: {article_date} < {cutoff_date}")
                self.run_loop = False  
            
            return is_old
        except Exception as e:
            self.logger.error(f"❌ Error checking article date: {e}")
            return False
    
    def fix_data_doc(self,data_doc):
        
        
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
        fixed_doc = {}
        for key in ["author", "image", "url", "title", "time"]:
            fixed_doc[key] = data_doc.get(key, template[key])
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
        
        try:
            
            if self.config.get('skip_existing', True):
                if self.check_article_exists(article_data.get('url', '')):
                    return False
            
            
            self.db_client.update_one(
                {"url": article_data['url']},
                {"$set": self.fix_data_doc(article_data)},
                upsert=True
            )
            
            self.total_articles_scraped += 1
            self.articles_saved_this_page += 1  
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error saving article: {e}")
            return False
    
    def get_stats(self) -> Dict:
        
        return {
            'total_articles_scraped': self.total_articles_scraped,
            'skipped_urls': self.skipped_urls,
            'consecutive_skips': self.consecutive_skips,
            'pages_scraped': self.page_index - 1,
            'stopped_early': not self.run_loop
        }
    
    def log_stats(self):
        stats = self.get_stats()
        self.logger.info("=" * 60)
        self.logger.info("📊 SCRAPING STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"✅ Articles Scraped: {stats['total_articles_scraped']}")
        self.logger.info(f"⏭️  Articles Skipped: {stats['skipped_urls']}")
        self.logger.info(f"📄 Pages Processed: {stats['pages_scraped']}")
        self.logger.info(f"⏹️  Early Termination: {stats['stopped_early']}")
        self.logger.info("=" * 60)
    
    
    def get_grid_details(self):
        raise NotImplementedError("Subclass must implement get_grid_details()")
    
    def scrape_grid_data(self, html_content):
        raise NotImplementedError("Subclass must implement scrape_grid_data()")
    
    def parse_blog_details(self, url):
        raise NotImplementedError("Subclass must implement parse_blog_details()")
    
    def run(self):
        raise NotImplementedError("Subclass must implement run()")
