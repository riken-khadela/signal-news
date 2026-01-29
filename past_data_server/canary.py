from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, CANARY_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    "https://www.canarymedia.com/articles/p"
]

class Canary(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/canary"
        )
        self.grid_details = []

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(url + str(self.page_index))
            self.logger.info(f"Fetching: {url + str(self.page_index)}")
            
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
        """Extract article data from Canary Media search results"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        for children in data.find_all('article'):
            try:
                tmp = {
                    "author": "",
                    "image": "",
                    "url": "",
                    "title": "",
                    "time": "",
                    "category": ""
                }
                
                # author (required field)
                author_ele = children.find('p', {'class': "type-theta"})
                if not author_ele:
                    continue
                tmp['author'] = author_ele.get_text(strip=True)

                # time
                time_ele = children.find('time')
                if time_ele:
                    tmp['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
                    
                    # # UNIQUE: Parse date with specific format
                    # try:
                    #     date_obj = datetime.strptime(tmp['time'], "%d %B %Y")
                    #     # Check if too old
                    #     if self.is_article_too_old(date_obj, cutoff_year=2025):
                    #         break
                    # except:
                    #     pass

                # category
                category_ele = children.select_one("div p")
                if category_ele:
                    tmp['category'] = category_ele.get_text(strip=True)
                
                # image
                image_ele = children.find('img')
                if image_ele:
                    image_url = image_ele.get('src') if image_ele else None
                    tmp['image'] = image_url
                
                # link
                link_ele = children.find('a')
                if link_ele:
                    tmp['url'] = link_ele.get('href')
                
                if not tmp['url']:
                    continue
                # Check if exists (with skip tracking)
                if self.check_article_exists(tmp['url']):
                    continue
                
                # title
                title_tag = children.find('h3')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
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

            # summary
            summary_ele = data.find('div', {'class': 'prose-sans'})
            if summary_ele:
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            # UNIQUE: Extract details from paragraphs with dir='ltr'
            details['description']['details'] = '\n '.join([
                i.get_text() for i in data.find_all('p', {'dir': 'ltr'})
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
        self.logger.info("🚀 Starting Canary scraper")
        
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
        self.logger.info("✅ Canary scraper completed")

def main():
    Canary().run()
    
if __name__ == "__main__":
    main()
