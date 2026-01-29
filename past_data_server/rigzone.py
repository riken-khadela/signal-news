from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup, NavigableString, Tag
from requests import RequestException
from settings import get_request, RIGZONE_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

# UNIQUE: Multiple category URLs
URLS_list = [
    "https://www.rigzone.com/news/industry_headlines/",
    "https://www.rigzone.com/news/exploration/",
    "https://www.rigzone.com/news/production/",
    "https://www.rigzone.com/news/company_operations/",
    "https://www.rigzone.com/news/finance_and_investing/",
    "https://www.rigzone.com/news/alternative_energy/",
]
BASE_URL = "https://www.rigzone.com/news"

class RigZone(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/rigzone"
        )
        self.grid_details = []

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(f"{url}")
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
        """Extract article data from RigZone"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        divs = data.find_all('div', {'class': 'smallHeadline'})
        
        for blog in divs:
            try:
                tmp = {
                    "image": "",
                    "url": "",
                    "title": "",
                    "time": "",
                    "description": {
                        "summary": "",
                        "details": ""
                    }
                }

                # title
                title_tag = blog.find('a')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                if not title:
                    continue
                
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
                
                # summary
                summary_ele = blog.find('div', class_='description')
                if summary_ele:
                    src = summary_ele.get_text(strip=True)
                    tmp['description']['summary'] = src
                
                extracted_data.append(tmp)
                
            except Exception as e:
                self.logger.error(f"Error extracting data from article: {e}")

        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = grid
        try:
            data = BeautifulSoup(response.text, "html.parser")
            content_div = data.find('div', {'id': 'content'})
            
            # image
            if content_div:
                img_ele = content_div.find('img')
                if img_ele:
                    details['image'] = img_ele.get('src')
            
            # UNIQUE: Author with special formatting
            author_ele = data.find('div', {'class': 'articleAuthor'})
            if author_ele:
                details['author'] = author_ele.get_text(strip=True).replace('by\xa0', '').strip()
            
            # UNIQUE: Extract specific tags
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div', {'id': 'divArticleTextForDesktop'})
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
        """Main execution logic - UNIQUE: Multiple category URLs"""
        self.logger.info("🚀 Starting RigZone scraper")
        
        for url in URLS_list:
            self.logger.info(f"📂 Processing category: {url}")
            self.consecutive_skips = 0
            self.page_index += 1
            
            self.grid_details = []
            self.get_grid_details(url)
            
            if self.grid_details:
                self.check_db_grid()
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ RigZone scraper completed")

def main():
    RigZone().run()
    
if __name__ == "__main__":
    main()