from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup, NavigableString, Tag
from requests import RequestException
from settings import get_request, NANOWERK_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    "https://www.nanowerk.com/category-nanoresearch.php?page="
]
BASE_URL = "https://www.mining.com/"

class NanoWerk(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/nanowerk"
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
        """Extract article data from Nanowerk"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        # UNIQUE: Uses section with articles class
        section = data.find('section', class_='articles')
        if not section:
            return extracted_data
        
        divs = section.find_all('div', recursive=False)

        for blog in divs:
            try:
                tmp = {
                    "image": "",
                    "url": "",
                    "title": "",
                    "time": ""
                }

                # title
                title_tag = blog.find('h2')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
                # link
                link_ele = blog.find('a')
                if link_ele:
                    url = link_ele.get('href')
                    tmp['url'] = url
                
                if not tmp['url']:
                    continue
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(tmp['url']):
                    continue
                
                # image
                img_ele = blog.find('img')
                if img_ele:
                    src = img_ele.get('src')
                    tmp['image'] = src
                
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
            "author": ""
        }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # time from meta tag
            time_ele = data.find('meta', {'property': 'article:published_time'})
            if time_ele:
                details['time'] = parse_datetime_safe(time_ele.get('content'))
            
            # UNIQUE: Extract author from JSON-LD script
            author_ele = data.find('script', {'type': 'application/ld+json'})
            if author_ele:
                try:
                    author_list = json.loads(author_ele.get_text(strip=True))
                    if 'author' in author_list.keys():
                        if type(author_list['author']) == list:
                            author = author_list['author'][0].get('name', "")
                        else:
                            author = author_list['author'].get('name', "")
                        
                        details['author'] = author
                except:
                    pass
            
            # summary from meta tag
            summary_ele = data.find('meta', {'property': 'og:description'})
            if summary_ele:
                details['summary'] = summary_ele.get('content')
            
            # UNIQUE: Extract only <td> elements with specific allowed tags
            allowed_tags = {"em"}
            clean_tds = []
            for td in data.find_all("td"):
                valid = True

                for child in td.contents:
                    if isinstance(child, NavigableString):
                        continue
                    elif isinstance(child, Tag) and child.name in allowed_tags:
                        continue
                    else:
                        valid = False
                        break

                if valid:
                    text = td.get_text(strip=True)
                    if text:
                        clean_tds.append(text)
            
            details['description']['details'] = '\n'.join(clean_tds)
            
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
        self.logger.info("🚀 Starting Nanowerk scraper")
        
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
        self.logger.info("✅ Nanowerk scraper completed")

def main():
    NanoWerk().run()
    
if __name__ == "__main__":
    main()
