from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, CLEANENERGY_WIRE_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    "https://www.cleanenergywire.org/news"
]
BASE_URL = "https://www.cleanenergywire.org"

class CleanEnergyWire(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/cleanenergywire"
        )
        self.grid_details = []
        # UNIQUE: Starts at -1 (will become 0 on first increment)
        self.page_index = -1

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            # UNIQUE: First page has no parameter, subsequent pages use ?page=N
            if self.page_index == 0:
                done, response = get_request(url)
            else:
                done, response = get_request(url + '?page=' + str(self.page_index))
            
            self.logger.info(f"Fetching: {url}")
            
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
        """Extract article data from Clean Energy Wire"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        for children in data.find_all('div', {'class': 'views-row'}):
            try:
                tmp = {
                    "author": "",
                    "image": "",
                    "url": "",
                    "title": "",
                    "time": "",
                    "category": ""
                }

                # UNIQUE: Parse date with specific format
                time_ele = children.find('time')
                if time_ele:
                    tmp['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
                    # try:
                    #     date_obj = datetime.strptime(tmp['time'], "%d %b %Y - %H:%M")
                    #     # Check if too old
                    #     if self.is_article_too_old(date_obj, cutoff_year=2025):
                    #         break
                    # except:
                    #     pass

                # title
                title_tag = children.find('h2')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
                if title_tag:
                    # link
                    link_ele = title_tag.find('a')
                    if link_ele:
                        url = link_ele.get('href')
                        tmp['url'] = f"{BASE_URL}{url}" if BASE_URL not in url else url
                
                if not tmp['url']:
                    continue
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(tmp['url']):
                    continue
                
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
            }
        }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            # author
            author_ele = data.find('div', {'aria-label': 'Name of the Autor'})
            if author_ele:
                details['author'] = author_ele.get_text(strip=True)
            
            # UNIQUE: Extract specific tags (p and h2)
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div', {'class': 'textParagraphText'})
            if details_ele:
                texts = []
                for tag in details_ele.find_all(ALLOWED_TAGS, recursive=True):
                    text = tag.get_text(" ", strip=True)
                    if text:
                        texts.append(text)
                
                details['description']['details'] = ' \n'.join(texts)
            
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
                merged['created_at'] = datetime.now(ist)
                
                # Use save_article from BaseScraper
                if self.save_article(merged):
                    self.logger.info(f"✅ Saved: {merged['url']}")

                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        """Main execution logic"""
        self.logger.info("🚀 Starting Clean Energy Wire scraper")
        
        for url in URLS_list:
            self.logger.info(f"📂 Processing: {url}")
            # UNIQUE: Reset to -1 (will become 0 on first increment)
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
        self.logger.info("✅ Clean Energy Wire scraper completed")

def main():
    CleanEnergyWire().run()
    
if __name__ == "__main__":
    main()
