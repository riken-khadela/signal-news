from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, CNET_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/cnet")
from datetime import datetime, timedelta, timezone

import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)


# def get_all_links():
    

class Cnet:
    def __init__(self):
        
        self.grid_details = []
        self.page_index = 1
        self.run_loop = True
        self.limit = 200
        self.offset = 0
        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self):
        """Scrape the grid (listing) page."""
        while True :
            try:
                done, response = get_request(f"https://bender.prod.cnet.tech/api/neutron/sitemaps/cnet/articles/year/2025/web?limit={self.limit}&offset={self.offset}&apiKey=073ecda0-c8e1-42ea-8d06-60b4ee845981")
                # done, response = get_scrape_do_requests(URL)
                if not done:
                    logger.error(f"Request failed:")
                    continue
                
                self.grid_details.append(self.scrape_grid_data(response.json()))
                self.offset += self.limit
                if response.json().get('data',{}) == {}:
                    break
                if response.json().get('data',{}).get('paging',{}).get('total',0) <= self.offset :
                    break

                logger.info(f"Collected {len(self.grid_details)} grid items.")
                # return self.grid_details

            except RequestException as e:
                logger.error(f"Request error while fetching grid: {e}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error in get_grid_details: {e}")
                return []
        return self.grid_details

    def generate_cnet_absolute_url(self, item: dict) -> str:
        base = "https://www.cnet.com"

        # Extract hub path and normalize
        hub_path = item.get("metaData", {}).get("hubTopicPathString", "")
        parts = hub_path.split("^")

        # CNET uses the first two levels only
        path_parts = [
            p.lower()
            .replace("&", "and")
            .replace(" ", "-")
            for p in parts[:2]
        ]

        slug = item.get("slug")

        return f"{base}/{'/'.join(path_parts)}/{slug}/"

    def scrape_grid_data(self, json_response):
        """
        Extract article data from YourStory search results
        """
        data = json_response.get('data',{})
        data_dict = []
        for items in data.get('items',[]):
            tmp = {
                'url' : self.generate_cnet_absolute_url(items),
                'title' : items.get('title',''),
                'image' : items.get('path',{}).get('path',''),
                'dateCreated' : items.get('dateCreated',''),
                'dateUpdated' : items.get('dateUpdated',''),
                'datePublished' : items.get('datePublished',''),
            }
            data_dict.append(tmp)

        return data_dict

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"author":"","description": {
            "summary" : "",
            "details" : ""
        }}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            #  author
            author_ele = data.find('span',{'class':'c-globalAuthor_name'})
            if author_ele:
                details['author'] = author_ele.get_text(strip=True)

            # description
            summery_ele = data.find('p',{'class':'c-contentHeader_description'})
            if summery_ele:
                details['description']['summary'] = summery_ele.get_text(strip=True)
                
            details_ele = data.find('article')
            if details_ele :
                details['description']['details'] = details_ele.get_text()

        except Exception as e:
            logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid_items in self.grid_details:
            for grid in grid_items:
                try:
                    if news_details_client.find_one({"url": grid["url"]}):
                        logger.info(f"Updating (already in DB): {grid['url']}")
                        self.skipped_urls += 1
                        continue

                    done, response = get_request(grid["url"])
                    if not done:
                        logger.warning(f"Failed fetching: {grid['url']}")
                        continue
                    
                    details = self.separate_blog_details(response)
                    merged = {**details, **grid}
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
        while self.run_loop:
            self.page_index += 1
            self.grid_details = []
            self.get_grid_details()
            if self.grid_details:
                self.check_db_grid()

def main():
    Cnet().run()
    
# if __name__ == "__main__":
#     Cnet().run()
