from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, TEST_NEXT_WEB_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    "https://thenextweb.com/latest/page/"
]

class NextWeb(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/next_web"
        )
        self.grid_details = []

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            if self.page_index == 1:
                done, response = get_request(url.replace("/page/", ""))
            else :
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
        """Extract article data from The Next Web"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        main_children = data.find('main', {'class': 'c-split__main'})
        if not main_children:
            return extracted_data
        
        for children in main_children.find_all('article'):
            try:
                tmp = {
                    "author": "",
                    "image": "",
                    "url": "",
                    "title": "",
                }
                
                # author
                author_ele = children.find('a', {'data-event-action': "Author"})
                if author_ele:
                    tmp['author'] = author_ele.get_text(strip=True)
                
                # UNIQUE: Multiple image source attributes
                image_ele = children.find('img')
                if image_ele:
                    image_url = (image_ele.get("src") or image_ele.get("data-src") or image_ele.get("data-lazy-src"))
                    tmp['image'] = image_url
                
                # link
                link_ele = children.find('a')
                if link_ele:
                    url = f"https://thenextweb.com{link_ele.get('href')}" if "https://thenextweb.com" not in link_ele.get('href') else link_ele.get('href')
                    tmp['url'] = url
                
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
            },
            "time": '',
        }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # title
            title_ele = data.find('h1', {'class': 'c-header__heading'})
            if title_ele:
                details['title'] = title_ele.get_text(strip=True)
            
            main_article = data.find('div', {'class': 'c-articles'})
            
            if not main_article:
                self.logger.warning(f"Could not find main article container")
                return details
            
            # description summary
            summary_ele = main_article.find('p', {'class': 'c-header__intro'})
            if summary_ele:
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            # time
            time_ele = main_article.find('time')
            if time_ele:
                details['time'] = parse_datetime_safe(time_ele.get_text(strip=True))
            
            # UNIQUE: Extract specific tags
            ALLOWED_TAGS = ["p", "h3"]
            details_ele = main_article.find('div', {'id': 'article-main-content'})
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
        self.logger.info("🚀 Starting The Next Web scraper")
        
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
        self.logger.info("✅ The Next Web scraper completed")

def main():
    NextWeb().run()
    
if __name__ == "__main__":
    main()
