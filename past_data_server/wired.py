from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, THE_WIRED_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

# UNIQUE: Wired scrapes multiple categories
URLS_list = [
    "https://www.wired.com/category/business/?page=",
    "https://www.wired.com/category/science/?page="
]

class Wired(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/the_wired"
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
        """Extract article data from Wired search results"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        # UNIQUE: Wired uses nested div structure with summary-list__items
        for main_children in data.find_all('div', {'class': 'summary-list__items'}):
            for children in main_children.children:
                try:
                    tmp = {}
                    
                    # author
                    author_ele = children.find('span', {'class': 'rubric__name'})
                    if author_ele:
                        tmp['author'] = author_ele.get_text()
                    
                    # link
                    link_ele = children.find('a')
                    if link_ele:
                        href = link_ele.get('href')
                        tmp['url'] = f"https://www.wired.com{href}" if "https://www.wired.com" not in href else href
                    
                    # Check if exists (with skip tracking)
                    if 'url' in tmp and self.check_article_exists(tmp['url']):
                        continue
                    
                    # title
                    if link_ele:
                        tmp['title'] = link_ele.get_text('')
                    
                    # image
                    img_ele = children.find('img')
                    if img_ele:
                        tmp['image'] = img_ele.get('src')
                    
                    if tmp:
                        extracted_data.append(tmp)
                
                except Exception as e:
                    self.logger.error(f"Error extracting data from article: {e}")
        
        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {
            "description": {
                "summary": "",
                "details": ""
            },
            "time": ""
        }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # UNIQUE: Wired has specific content-header-text structure
            # description summary
            summery_ele = data.find('div', {'class': 'content-header-text'})
            if summery_ele:
                details['description']['summary'] = [i for i in summery_ele.children][-1].get_text()
            
            if not details['description']['summary']:
                summery_ele = data.find('div', {'data-testid': 'ContentHeaderAccreditation'})
                if summery_ele:
                    details['description']['summary'] = summery_ele.get_text()
            
            # description details
            details['description']['details'] = '\n '.join([
                i.get_text() for i in data.find_all('div', {'class': 'body__inner-container'})
            ])
            
            # time
            time_ele = data.find('time')
            if time_ele:
                details['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
                
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
                merged = {**grid, **details}

                # Use save_article from BaseScraper
                if self.save_article(merged):
                    self.logger.info(f"✅ Saved: {merged['url']}")

                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        """Main execution logic - UNIQUE: loops through multiple category URLs"""
        self.logger.info("🚀 Starting Wired scraper")
        
        # UNIQUE: Wired scrapes multiple categories
        for url in URLS_list:
            self.logger.info(f"📂 Processing category: {url}")
            self.page_index = 0  # Reset for each category
            self.consecutive_skips = 0  # Reset skip counter
            
            while self.should_continue_scraping():
                self.page_index += 1
                self.logger.info(f"📄 Processing page {self.page_index}")
                
                self.grid_details = []
                self.get_grid_details(url)
                
                if self.grid_details:
                    self.check_db_grid()
                else:
                    self.logger.warning("No articles found, moving to next category")
                    break
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ Wired scraper completed")

def main():
    Wired().run()
    
if __name__ == "__main__":
    main()
