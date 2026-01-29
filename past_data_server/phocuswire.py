from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
import requests
from requests import RequestException
from settings import get_request, PHOCUSWIRE_client as news_details_client, parse_datetime_safe, get_headers, get_proxy
from base_scraper import BaseScraper
from bs4 import NavigableString, Tag
import pytz

ist = pytz.timezone("Asia/Kolkata")

BASE_URL = "https://www.phocuswire.com"
# UNIQUE: Uses POST API endpoint
API_URL = "https://www.phocuswire.com/Dyna.asmx/PageContentList"

max_retries = 10

class PhocusWire(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/phocuswire"
        )
        self.grid_details = []

    def get_grid_details(self):
        """UNIQUE: Scrape using POST API"""
        # UNIQUE: Custom POST payload
        payload = json.dumps({
            "req": {
                "PageKey": "51735130",
                "WidgetId": "dab5d2f3-0bb2-475e-a17d-7a2d71b6b96c",
                "PageNumber": f"{self.page_index}"
            }
        })
        
        try:
            response = None
            for _ in range(max_retries):
                response = requests.request("POST", API_URL, headers=get_headers(), data=payload, proxies=get_proxy())
                if response.status_code == 200:
                    self.logger.info(f"✅ Success: {API_URL} [{response.status_code}] for {self.page_index}")
                    break
                else:
                    self.logger.warning(f"⚠️ Failed: {API_URL} [{response.status_code}] for {self.page_index}")

            if response.status_code != 200:
                self.logger.error(f"Request failed: {self.page_index}")
                return []
           
            self.grid_details = self.scrape_grid_data(response.json())
            self.logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            self.logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in get_grid_details: {e}")
            return []

    def scrape_grid_data(self, response: dict = {}):
        """UNIQUE: Extract article data from JSON response"""
        extracted_data = []
        data = response
        html_content = data.get('d')
        data = BeautifulSoup(html_content, 'html.parser')
        
        for item in data.select("div.item"):
            try:
                title_tag = item.select_one("a.title")
                title = title_tag.get_text(strip=True) if title_tag else None

                # UNIQUE: Extract author and time from author div
                author_div = item.select_one("div.author")
                author = None
                time = None
                if author_div:
                    name_tag = author_div.select_one("span.name")
                    author = name_tag.get_text(strip=True).replace("By ", "") if name_tag else None

                    text_parts = author_div.get_text(" ", strip=True).split("|")
                    if len(text_parts) > 1:
                        time = text_parts[-1].strip()

                img_tag = item.select_one("div.category-img img")
                image = img_tag.get("src") if img_tag else None
                
                url = title_tag.get("href") if title_tag else None
                if not url:
                    continue
                
                url = f'{BASE_URL}{url}' if BASE_URL not in url else url
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(url):
                    continue
                
                extracted_data.append({
                    "image": image,
                    "url": url,
                    "author": author,
                    "title": title,
                    "time": parse_datetime_safe(time),
                    "description": {
                        "summary": "",
                        "details": ""
                    }
                })
            except Exception as e:
                self.logger.error(f"Error extracting data from article: {e}")

        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = grid
        try:
            data = BeautifulSoup(response.text, "html.parser")
            content_div = data.find('div', {"itemprop": "articleBody"})
            
            # UNIQUE: Extract specific tags
            ALLOWED_TAGS = ["p", "h2"]
            if content_div:
                texts = []
                for tag in content_div.find_all(ALLOWED_TAGS, recursive=True):
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

                # UNIQUE: Pass grid to separate_blog_details
                details = self.separate_blog_details(response, grid)
                merged = {**grid, **details}
                merged['created_at'] = datetime.now(ist)

                # Use save_article from BaseScraper
                if self.save_article(merged):
                    self.logger.info(f"✅ Saved: {merged['url']}")

                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        """Main execution logic - UNIQUE: POST API-based scraping"""
        self.logger.info("🚀 Starting PhocusWire scraper")
        
        while self.should_continue_scraping():
            self.logger.info(f"📄 Processing page {self.page_index}")
            
            self.grid_details = []
            self.get_grid_details()
            
            if self.grid_details:
                self.check_db_grid()
            else:
                self.logger.warning("No articles found, stopping")
                break
            
            self.page_index += 1
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ PhocusWire scraper completed")

def main():
    PhocusWire().run()
    
if __name__ == "__main__":
    main()