from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
# from settings import get_request, get_scrape_do_requests, NEXT_WEB_client as news_details_client, yourstory_scrape_do_requests
from settings import get_request, get_scrape_do_requests, CLEANENERGY_WIRE_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/CleanEnergyWire")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://www.cleanenergywire.org/news"
]
BASE_URL = "https://www.cleanenergywire.org"
class CleanEnergyWire:
    def __init__(self):
        self.grid_details = []
        self.page_index = -1
        self.run_loop = True

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            if self.page_index == 0:
                done, response = get_request(url)
            else :
                done, response = get_request(url +'?page='+ str(self.page_index))
                
                
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
        for children in data.find_all('article',{'class':'m-node--list--teaser'}): 
            try:
                tmp = {
                    "author" : "",
                    "image" : "",
                    "url" : "",
                    "title" : "",
                    "time" : "",
                    "category" : ""
                }

                time_ele = children.find('span',{'class':'date-display-single'}) 
                if time_ele :
                    tmp['time'] = time_ele.get_text(strip=True)
                    date_obj = datetime.strptime(tmp['time'], "%d %b %Y - %H:%M")

                title_tag = children.find('h3')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
                if title_tag:
                    # link
                    link_ele = title_tag.find('a')
                    if link_ele :
                        url = link_ele.get('href')
                        tmp['url'] = f"{BASE_URL}{url}" if not BASE_URL in url else url
                    
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
            
            author_ele = data.find('span',{'class':'m-node--article--full__author'}) 
            if author_ele :
                details['author'] = author_ele.get_text(strip=True)
            summary_ele = data.find('div',{'class':'prose-sans'})
            if summary_ele :
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div',{'class':'m-paragraph--textonly'})
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
    CleanEnergyWire().run()
    
# if __name__ == "__main__":
#     CleanEnergyWire().run()
