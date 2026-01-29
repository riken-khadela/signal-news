from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, THE_WIRED_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/the_wired")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://www.wired.com/category/business/?page=",
    "https://www.wired.com/category/science/?page="
]

class Wired:
    def __init__(self):
        self.grid_details = []
        self.page_index = 0
        self.run_loop = True
        self.skipped_urls = 0

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(url + str(self.page_index))
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
        
        for main_children in data.find_all('div',{'class':'summary-list__items'}) : 
            for children in main_children.children :
                try:
                    tmp = {}
                    author_ele = children.find('span',{'class':'rubric__name'}) 
                    if author_ele :
                        tmp['author'] = author_ele.get_text()
                        
                    # link
                    link_ele = children.find('a')
                    if link_ele :
                        tmp['url'] = f"https://www.wired.com{link_ele.get('href')}" if not "https://www.wired.com" in link_ele.get('href') else link_ele.get('href')
                        
                    # title
                    link_ele = children.find('a')
                    if link_ele :
                        tmp['title'] = link_ele.get_text('')
                        
                    # image
                    img_ele = children.find('img')
                    if img_ele :
                        tmp['image'] = img_ele.get('src')
                    if tmp:
                        extracted_data.append(tmp)
            
                except Exception as e:
                    print(f"Error extracting data from article: {e}")
        
        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {
            "description": {
                "summary" : "",
                "details":""
                },
            "time":""}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # description
            summery_ele = data.find('div',{'class':'content-header-text'})
            if summery_ele :
                details['description']['summary'] = [i for i in summery_ele.children][-1].get_text()
            
            if not details['description']['summary'] :
                summery_ele = data.find('div',{'data-testid':'ContentHeaderAccreditation'})
                if summery_ele :
                    details['description']['summary'] = summery_ele.get_text()
                    
            if not details['description']['summary'] : breakpoint()
                
            details['description']['details'] = '\n '.join([ i.get_text() for i in data.find_all('div',{'class':'body__inner-container'})])
            details['time'] = data.find('time').get_text(strip=True)
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
    Wired().run()
    
# if __name__ == "__main__":
#     Wired().run()
