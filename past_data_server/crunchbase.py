from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup, NavigableString, Tag
from requests import RequestException
from settings import get_request, CRUNCHBASE_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    "https://news.crunchbase.com/page/"
]
BASE_URL = "https://news.crunchbase.com/"

class CrunchBase(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/crunchbase"
        )
        self.grid_details = []

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(f"{url + str(self.page_index)}/")
            self.logger.info(f"Fetching: {url + str(self.page_index)}/")
            
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
        """Extract article data from CrunchBase"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        divs = data.find_all('article')
        for blog in divs:
            try:
                tmp = {
                    "image": "",
                    "url": "",
                    "title": "",
                    "time": "",
                    "author": '',
                    "description": {
                        "details": "",
                        "summary": ""
                    }
                }

                # UNIQUE: Find title from multiple heading levels
                title_tag = (blog.find('h3') or blog.find('h2') or 
                           blog.find('h1') or blog.find('h4') or 
                           blog.find('h5') or blog.find('h6'))
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
                if not title:
                    continue
                
                # UNIQUE: Image uses data-src attribute
                img_ele = blog.find('img')
                if img_ele:
                    src = img_ele.get('data-src') if img_ele.get('data-src') else img_ele.get('src') if img_ele.get('src') else ""
                    tmp['image'] = src
                
                # link
                link_ele = blog.find('a')
                if link_ele:
                    url = link_ele.get('href')
                    tmp['url'] = f"{BASE_URL}{url}" if BASE_URL not in url else url
                
                if not tmp['url']:
                    continue
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(tmp['url']):
                    continue
                
                # time
                time_ele = blog.find('div', {'class': 'herald-date'})
                if time_ele:
                    tmp['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
                
                # author
                author_ele = blog.find('span', class_="author")
                if author_ele:
                    tmp['author'] = author_ele.get_text(strip=True).replace('By', '').strip()
                
                extracted_data.append(tmp)
                
            except Exception as e:
                self.logger.error(f"Error extracting data from article: {e}")

        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = {
            "description": {
                "summary": "",
                "details": ""
            }
        }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # summary from meta tag
            summary_ele = data.find('meta', {'property': 'og:description'})
            if summary_ele:
                details['summary'] = summary_ele.get('content')
            
            # time from meta tag
            time_ele = data.find('meta', {'property': 'og:updated_time'})
            if time_ele:
                details['time'] = parse_datetime_safe(time_ele.get('content'))
            
            # UNIQUE: Extract specific tags (p and h2)
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div', {'class': 'entry-content'})
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
        """Main execution logic"""
        self.logger.info("🚀 Starting CrunchBase scraper")
        
        for url in URLS_list:
            self.logger.info(f"📂 Processing: {url}")
            self.page_index = 0
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
        self.logger.info("✅ CrunchBase scraper completed")

def main():
    CrunchBase().run()
    
if __name__ == "__main__":
    main()
