from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, BETA_KIT_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    'https://betakit.com/page/'
]

class BetaKit(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/betakit"
        )
        self.grid_details = []

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(url + str(self.page_index))
            if not done:
                self.logger.error(f"Request failed: {url}")
                return []

            self.grid_details = self.scrape_grid_data(response.text)
            self.logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            self.logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in get_grid_details: {e}")
            return []

    def scrape_grid_data(self, html_content):
        """Extract article data from BetaKit search results"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        # UNIQUE: BetaKit uses grid-layout structure
        main_children = data.find('div', {'class': 'grid-layout'})
        if not main_children:
            return extracted_data
        
        for children in main_children.find_all('article'):
            try:
                tmp = {}
                
                # author
                author_ele = children.find('span', {'class': 'author'})
                if author_ele:
                    tmp['author'] = author_ele.get_text(strip=True)
                
                # image
                image_ele = children.find('img')
                if image_ele:
                    tmp['image'] = image_ele.get('src')
                
                # link
                link_ele = children.find('a')
                if link_ele:
                    tmp['url'] = f"{link_ele.get('href')}"
                
                # Check if exists (with skip tracking)
                if 'url' in tmp and self.check_article_exists(tmp['url']):
                    continue
                
                # title
                title_ele = children.find('h2')
                if title_ele:
                    tmp['title'] = title_ele.get_text(strip=True)
                
                # time
                time_ele = children.find('span', {'class': 'entry-date'})
                if time_ele:
                    tmp['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
                
                extracted_data.append(tmp)
            except Exception as e:
                self.logger.error(f"Error extracting data from article: {e}")
        
        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}, "time": ''}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # description summary
            summary_ele = data.find('div', {'class': 'manual-excerpt'})
            if summary_ele:
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            # description details
            details_ele = data.find('article')
            if details_ele:
                details['description']['details'] = ' \n'.join([
                    i.get_text(strip=True) for i in details_ele.find_all('p')
                ])
        except Exception as e:
            self.logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
            try:
                done, response = get_request(f"{grid['url']}")
                if not done:
                    self.logger.warning(f"Failed fetching: {grid['url']}")
                    continue

                details = self.separate_blog_details(response)
                merged = {**details, **grid}
                merged['created_at'] = datetime.now(ist)
                
                # Use save_article from BaseScraper
                if self.save_article(merged):
                    self.logger.info(f"✅ Saved: {merged['url']}")

                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        """Main execution logic"""
        self.logger.info("🚀 Starting BetaKit scraper")
        
        for url in URLS_list:
            self.logger.info(f"📂 Processing: {url}")
            self.page_index = -1
            self.consecutive_skips = 0
            
            while self.should_continue_scraping():
                self.page_index += 1
                self.logger.info(f"📄 Processing page {self.page_index}")
                
                self.grid_details = []
                self.get_grid_details(url)
                
                if self.grid_details:
                    self.check_db_grid()
                else:
                    self.logger.warning("No articles found, stopping")
                    break
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ BetaKit scraper completed")

def main():
    BetaKit().run()
    
if __name__ == "__main__":
    main()
