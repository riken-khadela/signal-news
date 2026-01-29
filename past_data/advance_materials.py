from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
# from settings import get_request, get_scrape_do_requests, NEXT_WEB_client as news_details_client, yourstory_scrape_do_requests
from settings import get_request, get_scrape_do_requests, ADVANCE_MATERIALS_MAGAZINE_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/ADVANCE_MATERIALS")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://www.advancedmaterialsmagazine.com/public/news/all?page="
]
BASE_URL = "https://www.advancedmaterialsmagazine.com/public/news/"
class AdvanceMaterials:
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
            done, response = get_request(f"{url + str(self.page_index)}")
                
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
        main_blogs_list = data.find('div',{'class':'blog-list'})
        if not main_blogs_list :
            return extracted_data
        
        for blog in main_blogs_list.find_all('div',{'class':'blog-box'}): 
            try:
                tmp = {
                    "author" : "",
                    "image" : "",
                    "url" : "",
                    "title" : "",
                    "time" : "",
                    "category" : ""
                }

                small_ele = blog.find_all('small')
                if small_ele :
                    if len(small_ele) < 1 : continue
                    
                    category = small_ele[0]
                    tmp['category'] = category.get_text(strip=True)
                    
                    time_ele = small_ele[-1]
                    tmp['time'] = time_ele.get_text(strip=True)
                    date_obj = datetime.strptime(tmp['time'], "%d %b %Y")

                title_tag = blog.find('h4')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
                # link
                link_ele = blog.find('a')
                if link_ele :
                    url = link_ele.get('href')
                    tmp['url'] = f"{BASE_URL}{url}" if not BASE_URL in url else url
                
                # link
                img_ele = blog.find('img')
                if img_ele :
                    url = img_ele.get('src')
                    tmp['image'] = url
                    
                if not tmp['url']:
                    continue
                
                
                extracted_data.append(tmp)
                
            except Exception as e:
                print(f"Error extracting data from article: {e}")

        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {
            "description": {
                    "summary" : "",
                    "details" : ""
                }
            }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            author_ele = data.find('div',{'class':'author-cont'}) 
            if author_ele :
                details['author'] = author_ele.get_text(strip=True)
                
            container = data.find('div',{'class':'container'})
            details['description']['details'] = '\n'.join(dict.fromkeys( span.get_text(strip=True) for span in container.find_all('span') if span.get_text(strip=True) ))
            
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
                
                
                details = self.separate_blog_details(response)
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
    AdvanceMaterials().run()
    
# if __name__ == "__main__":
#     AdvanceMaterials().run()
