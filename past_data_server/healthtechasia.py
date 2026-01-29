from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, HEALTHTECHASIA_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
from dateutil.relativedelta import relativedelta
import re
import pytz

ist = pytz.timezone("Asia/Kolkata")

# UNIQUE: Multiple URLs
URLS_list = [
    'https://healthtechasia.co/page/',
    'https://healthtechasia.co/category/news/page/'
]

# UNIQUE: Custom relative time parser
def parse_relative_time(text: str) -> datetime | None:
    """Parse relative time strings like '2 hours ago'."""
    text = text.lower().strip()
    now = datetime.now(timezone.utc)

    if text in {"just now", "now"}:
        return now

    match = re.match(r'(\d+)\s+(minute|min|hour|day|week|month|year)s?(?:\s+ago)?', text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)

        if unit.startswith("min"):
            return now - timedelta(minutes=value)
        if unit.startswith("hour"):
            return now - timedelta(hours=value)
        if unit.startswith("day"):
            return now - timedelta(days=value)
        if unit.startswith("week"):
            return now - timedelta(weeks=value)
        if unit.startswith("month"):
            return now - relativedelta(months=value)
        if unit.startswith("year"):
            return now - relativedelta(years=value)

    return datetime.strptime(text, "%B %d, %Y")

class HealthTechAsia(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/healthtechasia"
        )
        self.grid_details = []

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(url + str(self.page_index) + '/')
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
        """Extract article data from HealthTech Asia"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []

        for children in data.find_all('div', {'class': 'bs-blog-post'}):
            try:
                tmp = {
                    "url": "",
                    "author": "",
                    "description": {
                        "summary": "",
                        "details": ""
                    },
                    "image": "",
                    "time": "",
                    "title": ""
                }
                
                # link
                link_ele = children.find('a')
                if link_ele:
                    tmp['url'] = f"{link_ele.get('href')}"
                
                if not tmp['url']:
                    continue
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(tmp['url']):
                    continue
                
                # title
                title_ele = children.find('h4')
                if title_ele:
                    tmp['title'] = title_ele.get_text(strip=True)
                
                # description
                desc_ele = children.find('p')
                if desc_ele:
                    tmp['description']['summary'] = desc_ele.get_text(strip=True)
                
                extracted_data.append(tmp)
            except Exception as e:
                self.logger.error(f"Error extracting data from article: {e}")
        
        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = grid
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # author
            author_ele = data.find('a', class_='bs-author-pic')
            if author_ele:
                details['author'] = author_ele.get_text(strip=True).replace('By ', '')
            
            # time
            time_ele = data.find('time')
            if time_ele:
                time = time_ele.get('datetime')
                details['time'] = parse_datetime_safe(time if time else time_ele.get_text(strip=True))
            
            # UNIQUE: Extract image from CSS background-image
            img_ele_div = data.find('div', class_='back-img')
            if img_ele_div:
                style = img_ele_div.get('style')
                match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                image_url = match.group(1) if match else None
                details['image'] = image_url
            
            # UNIQUE: Only extract direct <p> children of article
            details_ele = data.find('article')
            if details_ele:
                details['description']['details'] = ' \n'.join([
                    i.get_text(strip=True) for i in details_ele.children if i.name == "p"
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
        """Main execution logic - UNIQUE: Multiple URLs"""
        self.logger.info("🚀 Starting HealthTech Asia scraper")
        
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
        self.logger.info("✅ HealthTech Asia scraper completed")

def main():
    HealthTechAsia().run()
    
if __name__ == "__main__":
    main()