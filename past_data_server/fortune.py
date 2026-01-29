from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, FORTUNE_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
from dateutil.relativedelta import relativedelta
import re
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    'https://fortune.com/section/latest/page/',
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

class Fortune(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/fortune"
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
        """Extract article data from Fortune"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        # UNIQUE: Uses data-cy attribute
        main_children = data.find_all('div', {'data-cy': 'article-card-wrapper'})
        if not main_children:
            return extracted_data
        
        for children in main_children:
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
                
                # image
                image_ele = children.find('img')
                if image_ele:
                    tmp['image'] = image_ele.get('src')
                
                # link
                link_ele = children.find('a')
                if link_ele:
                    tmp['url'] = f"{link_ele.get('href')}"
                
                if not tmp['url']:
                    continue
                
                # Check if exists (with skip tracking)
                print(tmp['url'])
                if self.check_article_exists(tmp['url']):
                    continue
                
                # title (try h3 first, then h2)
                title_ele = children.find('h3') if children.find('h3') else children.find('h2')
                if title_ele:
                    tmp['title'] = title_ele.get_text(strip=True)
                
                # author
                author_ele = children.find('div', {'class': 'card-authors'})
                if author_ele:
                    tmp['author'] = author_ele.get_text(strip=True)
                
                # UNIQUE: Parse relative time
                time_ele = children.find('span', class_="card-date")
                if time_ele:
                    try:
                        tmp['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
                    except:
                        tmp['time'] = time_ele.get_text(strip=True)
                
                extracted_data.append(tmp)
            except Exception as e:
                self.logger.error(f"Error extracting data from article: {e}")
        
        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = grid
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # details
            details_ele = data.find('article', class_='article-content')
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
        self.logger.info("🚀 Starting Fortune scraper")
        
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
        self.logger.info("✅ Fortune scraper completed")

def main():
    Fortune().run()
    
if __name__ == "__main__":
    main()