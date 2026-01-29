from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
# from settings import get_request, get_scrape_do_requests, NEXT_WEB_client as news_details_client, yourstory_scrape_do_requests
from settings import get_request, get_scrape_do_requests, CANARY_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/Canary")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://www.canarymedia.com/articles/p"
]
class Canary:
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
            done, response = get_request(url + str(self.page_index))
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
        
        for children in data.find_all('article'): 
            try:
                tmp = {
                    "author" : "",
                    "image" : "",
                    "url" : "",
                    "title" : "",
                    "time" : "",
                    "category" : ""
                }
                author_ele = children.find('p',{'class':"type-theta"}) 
                if author_ele :
                    tmp['author'] = author_ele.get_text(strip=True)
                else:
                    continue

                time_ele = children.find('time') 

                if time_ele :
                    tmp['time'] = time_ele.get_text(strip=True)
                    date_obj = datetime.strptime(tmp['time'], "%d %B %Y")

                category_ele = children.select_one("div p")
                if category_ele :
                    tmp['category'] = category_ele.get_text(strip=True)
                    
                # image
                image_ele = children.find('img')
                if image_ele :
                    image_url = image_ele['src'] if image_ele and image_ele.get('src') else None
                    tmp['image'] = image_url
                    
                # link
                link_ele = children.find('a')
                if link_ele :
                    url = link_ele.get('href')
                    tmp['url'] = url
                    
                if not tmp['url']:
                    continue
                
                title_tag = children.find('h3')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
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

            summary_ele = data.find('div',{'class':'prose-sans'})
            if summary_ele :
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            details['description']['details'] = '\n '.join([ i.get_text() for i in data.find_all('p',{'dir':'ltr'})])
            
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
                else:
                    break
def main():
    Canary().run()
    
# if __name__ == "__main__":
#     Canary().run()
