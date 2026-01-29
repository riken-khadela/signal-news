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
from settings import get_request, get_scrape_do_requests, HEALTHTECHMAGAZINE_client as news_details_client, yourstory_scrape_do_requests, get_headers, get_proxy
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/HealthTechMagazine")
from datetime import datetime, timedelta, timezone
from bs4 import NavigableString, Tag

BASE_URL = "https://healthtechmagazine.net"
url = "https://healthtechmagazine.net/views/ajax"
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

max_retries = 10

class HealthTechMagazine:
    def __init__(self):
        self.grid_details = []
        self.page_index = 0
        self.run_loop = True

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self,):
        """Scrape the grid (listing) page."""
        

        params = {
            "_wrapper_format": "drupal_ajax",
            "view_name": "article_listing",
            "view_display_id": "by_term_load",
            "view_args": "9046/all/all/61591",
            "view_path": "/taxonomy/term/9046",
            "pager_element": 0,
            "page": self.page_index,
            "_drupal_ajax": 1,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://healthtechmagazine.net/artificial-intelligence",
        }

        try:
            response = None

            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=30
                    )

                    if response.status_code == 200:
                        logger.info(
                            f"✅ Success: HealthTech grid page {self.page_index}"
                        )
                        break
                    else:
                        logger.warning(
                            f"⚠️ Failed page {self.page_index} "
                            f"[{response.status_code}] attempt {attempt + 1}"
                        )

                except Exception as e:
                    logger.warning(
                        f"⚠️ Error page {self.page_index} attempt {attempt + 1}: {e}"
                    )

                time.sleep(1)

            if not response or response.status_code != 200:
                logger.error(f"❌ Request failed for page {self.page_index}")
                return []

            # Drupal AJAX returns JSON commands; parsing happens downstream
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
        html_content = ''
        for command in data: 
            if command['command'] == 'insert' :
                if command['method'] == 'infiniteScrollInsertView' or 'replaceWith' :
                    html_content = command['data']
                    break
                
        data = BeautifulSoup(html_content, 'html.parser')
        
        for item in data.find('div', class_='cdw-v3-article-listing__wrapper').children : 
            if item.find("h3") == -1 :
                continue
            
            title_tag = item.find("h3")
            title = title_tag.get_text(strip=True) if title_tag else ""

            img_tag = item.select_one("img")
            image = img_tag.get("src") if img_tag else ""
            url = item.find("a").get('href') if item.find("a") else ""
            if not url :
                continue
            
            url = f'{BASE_URL}{url}' if not '{BASE_URL}/' in url else url
            extracted_data.append({
                    "image" : image,
                    "url" : url,
                    "author": "",
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
            summary_ele = data.find('div',class_='subtitle')
            if summary_ele:
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            author_ele = data.find('a',{'rel':'author'})
            if author_ele:
                details['author'] = author_ele.get_text(strip=True)
            
            time_ele = data.find('div',class_='pw-layout-vertical')
            if time_ele:
                details['time'] = ' '.join([ i.get_text(strip=True) for i in time_ele.find_all('span')][1:])
            
            image_div_ele = data.find('div',{'id':'article_key_image'})
            if image_div_ele:
                time_ele = image_div_ele.find('img')
                src = time_ele.get('src') 
                if src :
                    src = f'{BASE_URL}{src}' if not BASE_URL in src else src
                    details['image'] = src
            
            article_ele = data.find('article', class_='node--view-mode-full')
            if article_ele :
                content_div = article_ele.find('div', {"class":"content"})
                
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
    HealthTechMagazine().run()