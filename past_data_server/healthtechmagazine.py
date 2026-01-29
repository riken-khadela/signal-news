from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
import requests
from requests import RequestException
from settings import get_request, HEALTHTECHMAGAZINE_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
from bs4 import NavigableString, Tag
import pytz

ist = pytz.timezone("Asia/Kolkata")

BASE_URL = "https://healthtechmagazine.net"
# UNIQUE: Uses AJAX API endpoint
API_URL = "https://healthtechmagazine.net/views/ajax"

max_retries = 10

class HealthTechMagazine(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/healthtechmagazine"
        )
        self.grid_details = []

    def get_grid_details(self):
        """UNIQUE: Scrape using AJAX API"""
        # UNIQUE: Custom API parameters
        params = {
            "_wrapper_format": "drupal_ajax",
            "view_name": "article_listing",
            "view_display_id": "by_term_load",
            "view_args": "9046/all/all/61591",
            "view_path": "/taxonomy/term/9046",
            "pager_element": 0,
            "page": self.page_index,
            "_drupal_ajax": 1,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://healthtechmagazine.net/artificial-intelligence",
        }

        try:
            response = None

            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        API_URL,
                        headers=headers,
                        params=params,
                        timeout=30
                    )

                    if response.status_code == 200:
                        self.logger.info(
                            f"✅ Success: HealthTech grid page {self.page_index}"
                        )
                        break
                    else:
                        self.logger.warning(
                            f"⚠️ Failed page {self.page_index} "
                            f"[{response.status_code}] attempt {attempt + 1}"
                        )

                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Error page {self.page_index} attempt {attempt + 1}: {e}"
                    )

                time.sleep(1)

            if not response or response.status_code != 200:
                self.logger.error(f"❌ Request failed for page {self.page_index}")
                return []

            # UNIQUE: Drupal AJAX returns JSON commands
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
        html_content = ''
        
        # UNIQUE: Parse JSON commands to extract HTML
        for command in data:
            if command['command'] == 'insert':
                if command['method'] == 'infiniteScrollInsertView' or 'replaceWith':
                    html_content = command['data']
                    break
        
        data = BeautifulSoup(html_content, 'html.parser')
        wrapper = data.find_all('div', class_='cdw-v3-article-listing-item')
        if not wrapper:
            return extracted_data
        
        for item in wrapper:
            if item.find("h3") == -1:
                continue
            
            try:
                title_tag = item.find("h3")
                title = title_tag.get_text(strip=True) if title_tag else ""

                img_tag = item.select_one("img")
                image = img_tag.get("src") if img_tag else ""
                
                url = item.find("a").get('href') if item.find("a") else ""
                if not url:
                    continue
                
                url = f'{BASE_URL}{url}' if BASE_URL not in url else url
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(url):
                    continue
                
                extracted_data.append({
                    "image": image,
                    "url": url,
                    "author": "",
                    "title": title,
                    "time": "",
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
            
            # summary
            summary_ele = data.find('div', class_='subtitle')
            if summary_ele:
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            # author
            author_ele = data.find('a', {'rel': 'author'})
            if author_ele:
                details['author'] = author_ele.get_text(strip=True)
            
            # time
            time_ele = data.find('div', class_='pw-layout-vertical')
            if time_ele:
                details['time'] = parse_datetime_safe(' '.join([
                    i.get_text(strip=True) for i in time_ele.find_all('span')
                ][1:]))
            
            # image
            image_div_ele = data.find('div', {'id': 'article_key_image'})
            if image_div_ele:
                img_ele = image_div_ele.find('img')
                if img_ele:
                    src = img_ele.get('src')
                    if src:
                        src = f'{BASE_URL}{src}' if BASE_URL not in src else src
                        details['image'] = src
            
            # UNIQUE: Extract specific tags from article content
            article_ele = data.find('article', class_='node--view-mode-full')
            if article_ele:
                content_div = article_ele.find('div', {"class": "content"})
                
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
        """Main execution logic - UNIQUE: AJAX-based scraping"""
        self.logger.info("🚀 Starting HealthTech Magazine scraper")
        
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
        self.logger.info("✅ HealthTech Magazine scraper completed")

def main():
    HealthTechMagazine().run()
    
if __name__ == "__main__":
    main()