from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
import requests
import json
from requests import RequestException
# from settings import get_request, get_scrape_do_requests, NEXT_WEB_client as news_details_client, yourstory_scrape_do_requests
from settings import get_request, get_scrape_do_requests, PHOCUSWIRE_client as news_details_client, yourstory_scrape_do_requests, get_headers, get_proxy
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/PhocusWire")
from datetime import datetime, timedelta, timezone
from bs4 import NavigableString, Tag
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

BASE_URL = "https://www.phocuswire.com"
url = "https://www.phocuswire.com/Dyna.asmx/PageContentList"

max_retries = 10

class PhocusWire:
    def __init__(self):
        self.grid_details = []
        self.page_index = 0
        self.run_loop = True

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self,):
        """Scrape the grid (listing) page."""
        
        payload = json.dumps({
                "req": {
                    "PageKey": "51735130",
                    "WidgetId": "dab5d2f3-0bb2-475e-a17d-7a2d71b6b96c",
                    "PageNumber": f"{self.page_index}"
                }
            })
        try:
            for _ in range(max_retries):
                response = requests.request("POST", url, headers=get_headers(), data=payload, proxies=get_proxy())
                if response.status_code == 200:
                    logger.info(f"✅ Success: {url} [{response.status_code}] for {self.page_index}")
                    break
                else:
                    logger.warning(f"⚠️ Failed: {url} [{response.status_code}] for {self.page_index}")

            if response.status_code != 200:
                logger.error(f"Request failed: {self.page_index}")
                return []
           
            self.grid_details = self.scrape_grid_data(response.json())
            logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_grid_details: {e}")
            return []

    def scrape_grid_data(self, response : dict = {}):
        """
        Extract article data from YourStory search results
        """
        extracted_data = []
        data = response
        html_content = data.get('d')
        data = BeautifulSoup(html_content, 'html.parser')
        
        for item in data.select("div.item"):
            title_tag = item.select_one("a.title")
            title = title_tag.get_text(strip=True) if title_tag else None

            author_div = item.select_one("div.author")
            author = None
            time = None
            if author_div:
                name_tag = author_div.select_one("span.name")
                author = name_tag.get_text(strip=True).replace("By ", "") if name_tag else None

                text_parts = author_div.get_text(" ", strip=True).split("|")
                if len(text_parts) > 1:
                    time = text_parts[-1].strip()

            img_tag = item.select_one("div.category-img img")
            image = img_tag.get("src") if img_tag else None
            url = title_tag.get("href") if title_tag else None
            if not url :
                continue
            
            url = f'{BASE_URL}{url}' if not '{BASE_URL}/' in url else url
            extracted_data.append({
                    "image" : image,
                    "url" : url,
                    "author": author,
                    "title" : title,
                    "time" : time,
                    "description": {
                        "summary" : "",
                        "details" : ""
                    }
                })

        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = grid
        try:
            data = BeautifulSoup(response.text, "html.parser")
            content_div = data.find('div', {"itemprop":"articleBody"})
            
            ALLOWED_TAGS = ["p", "h2"]
            if content_div :
                texts = []
                for tag in content_div.find_all(ALLOWED_TAGS, recursive=True):
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
                self.skipped_urls = 0
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
        while True :
            if self.skipped_urls >= 50: break
            #         break
                
            self.grid_details = []
            self.get_grid_details()
            if self.grid_details:
                self.check_db_grid()
            self.page_index += 1


def main():
    PhocusWire().run()