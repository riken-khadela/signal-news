from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
# from settings import get_request, get_scrape_do_requests, NEXT_WEB_client as news_details_client, yourstory_scrape_do_requests
from settings import get_request, get_scrape_do_requests, CRUNCHBASE_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/CrunchBase")
from datetime import datetime, timedelta, timezone
from bs4 import NavigableString, Tag
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://news.crunchbase.com/page/"
]
BASE_URL = "https://news.crunchbase.com/"

class CrunchBase:
    def __init__(self):
        self.grid_details = []
        self.page_index = 0
        self.run_loop = True

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(f"{url + str(self.page_index)}/")
                
            print(f"{url + str(self.page_index)}")
            # done, response = get_scrape_do_requests(url)
            if not done:
                logger.error(f"Request failed: {url}")
                return []

           
            self.grid_details = self.scrape_grid_data(response.text)
            logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_grid_details: {e}")
            return []

    def scrape_grid_data(self, html_content):
        """
        Extract article data from YourStory search results
        """
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        divs = data.find_all('article')
        for blog in divs: 
            try:
                tmp = {
                    "image" : "",
                    "url" : "",
                    "title" : "",
                    "time" : "",
                    "author" : '',
                    "description" : {
                        "details" : "",
                        "summary" : ""
                    }
                }

                title_tag = blog.find('h3') if blog.find('h3') else blog.find('h2') if blog.find('h2') else blog.find('h1') if blog.find('h1') else blog.find('h4') if blog.find('h4') else blog.find('h5') if blog.find('h5') else blog.find('h6') 
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                if not title :
                    continue
                
                # link
                img_ele = blog.find('img')
                if img_ele :
                    src = img_ele.get('data-src')
                    tmp['image'] = src
                    
                # link
                link_ele = blog.find('a')
                if link_ele :
                    url = link_ele.get('href') 
                    tmp['url'] =  f"{BASE_URL}{url}" if not BASE_URL in url else url 
                    
                time_ele = blog.find('div',{'class':'herald-date'})
                if time_ele :
                    time = time_ele.get_text(strip=True) 
                    tmp['time'] = time
                    
                author_ele = blog.find('span', class_ = "author")
                if author_ele :
                    tmp['author'] = author_ele.get_text(strip=True).replace('By','').strip()
                
                if not tmp['url']:
                    continue
                extracted_data.append(tmp)
                
            except Exception as e:
                print(f"Error extracting data from article: {e}")

        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = {
            "description": {
                    "summary" : "",
                    "details" : ""
                }
            }
        try:
            data = BeautifulSoup(response.text, "html.parser")
                
            summary_ele = data.find('meta',{'property':'og:description'}) 
            if summary_ele :
                details['summary'] = summary_ele.get('content')
                
            time_ele = data.find('meta',{'property':'og:updated_time'}) 
            if time_ele :
                details['time'] = time_ele.get('content')
                
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div',{'class':'entry-content'})
            if details_ele :
                texts = []
                for tag in details_ele.find_all(ALLOWED_TAGS, recursive=True):
                    text = tag.get_text(" ", strip=True)
                    if text:
                        texts.append(text)
                        
                details['description']['details'] = ' \n'.join(texts)
            
        except Exception as e:
            logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
            try:
                
                if news_details_client.find_one({"url": grid["url"]}):
                        logger.info(f"Updating (already in DB): {grid['url']}")
                        self.skipped_urls += 1
                        continue

                done, response = get_request(f"{grid['url']}")
                if not done:
                    logger.warning(f"Failed fetching: {grid['url']}")
                    continue
                
                
                details = self.separate_blog_details(response, grid)
                merged = {**grid, **details}
                merged['created_at'] = ist_time
                news_details_client.update_one(
                    {"url": merged["url"]},
                    {"$set": merged},
                    upsert=True
                )
                logger.info(f"Inserted new article: {merged['url']}")

                time.sleep(1) 
            except Exception as e:
                logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        for url in URLS_list :
            self.skipped_urls = 0
            
            while True:
                if self.skipped_urls >= 50: break
                
                self.page_index += 1
                self.grid_details = []
                self.get_grid_details(url)
                if self.grid_details:
                    self.check_db_grid()


def main():
    CrunchBase().run()
# if __name__ == "__main__":
#     CrunchBase().run()
