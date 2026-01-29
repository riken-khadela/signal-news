from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, TECH_EU_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
from dateutil.relativedelta import relativedelta
import re
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    "https://tech.eu/page/"
]

# UNIQUE: Custom time parsing functions
def parse_relative_time(text: str) -> datetime | None:
    """Parse relative time strings like '2 hours ago'."""
    text = text.lower().strip()
    now = datetime.now(timezone.utc)

    if text in {"just now", "now"}:
        return now

    match = re.match(r'(\d+)\s+(minute|min|hour|day|week|month|year)s?(?:\s+ago)?', text)
    if not match:
        return None

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

    return None

def parse_absolute_date(text: str) -> datetime | None:
    """Parse absolute dates like '01 December 2025'."""
    formats = [
        "%d %B %Y",
        "%B %d, %Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

def parse_time(text: str) -> datetime | None:
    """Try parsing as relative time first, then absolute date."""
    result = parse_relative_time(text)
    if result is not None:
        return result
    return parse_absolute_date(text)

class TechEu(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/tech_eu"
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
        """Extract article data from Tech.eu"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        main_children = data.find_all('div', {'class': 'post-card'})
        if not main_children:
            return extracted_data
        
        for children in main_children:
            try:
                tmp = {
                    "title": "",
                    "author": "",
                    "image": "",
                }
                
                # author
                author_ele = children.find('a', {'class': "post-author-name"})
                if author_ele:
                    tmp['author'] = author_ele.get_text(strip=True)
                
                # UNIQUE: Extract from data-srcset
                image_ele = children.find('img')
                if image_ele:
                    srcset = image_ele.get('data-srcset')
                    if srcset:
                        tmp['image'] = srcset.split(',')[-1].strip().split(' ')[0].strip()
                
                # title
                title_ele = children.find('div', {'class': 'post-title'})
                if title_ele:
                    tmp['title'] = title_ele.get_text(strip=True)
                    
                    # link
                    link_ele = title_ele.find('a')
                    if link_ele:
                        url = link_ele.get('href')
                        tmp['url'] = url
                
                if not tmp.get('url'):
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
            
            # description summary
            summary_ele = data.find('div', {'class': 'single-post-summary'})
            if summary_ele:
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            # UNIQUE: Parse time using custom function
            time_ele = data.find('span', {'class': 'sp-date'})
            if time_ele:
                details['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
            
            # UNIQUE: Extract specific tags
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div', {'class': 'single-post-content'})
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
        self.logger.info("🚀 Starting Tech.eu scraper")
        
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
        self.logger.info("✅ Tech.eu scraper completed")

def main():
    TechEu().run()
    
if __name__ == "__main__":
    main()
