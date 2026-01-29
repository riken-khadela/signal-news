from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, HEALTHCAREASIAMAGAZINE_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
from datetime import datetime, timedelta, timezone
import re

logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/HealthCareAsiaMagazine")
URLS_list = [
    'https://healthcareasiamagazine.com/news?page=',
]
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

class HealthCareAsiaMagazine:
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
            done, response = get_request(url + str(self.page_index) )
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
        section = data.find('section',{'id':'block-responsive-content'})
        for children in section.find('div',{'class':'view-content'}).children: 
            if not children.find('h2') or children.find('h2') == -1 :
                continue
            
            
            try:
                tmp = {
                    "url": "",
                    "author": "",
                    "description": {
                        "summary": "",
                        "details": ""
                    },
                    "image": "",
                    "time": "",
                    "title": ""
                }
                    
                # link
                link_ele = children.find('a')
                if link_ele :
                    tmp['url'] = f"{link_ele.get('href')}"
                    
                # title
                title_ele = children.find('h2')
                if title_ele :
                    tmp['title'] = title_ele.get_text(strip=True)
                
                # description
                desc_ele = children.find('div',{'class':'item__description'})
                tmp['description'] = {}
                if desc_ele :
                    tmp['description']['summary'] = desc_ele.get_text(strip=True)
                    
                extracted_data.append(tmp)
            except Exception as e:
                print(f"Error extracting data from article: {e}")
    
        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = grid
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            author_ele = data.find('div',class_='nf-submitted-by')
            if author_ele :
                details['author'] = author_ele.get_text(strip=True)
            
            time_ele = data.find('time')
            if time_ele :
                details['time'] = time_ele.get('datetime')
                
            img_ele_div = data.find('div', class_='field--name-field-image')
            if img_ele_div :
                img_ele = img_ele_div.find('img')
                if img_ele :
                    details['image'] = img_ele.get('src')
                
            details_ele = data.find('div',class_ = 'nf__description')
            if details_ele :
                details['description']['details'] = ' \n'.join([i.get_text(strip=True) for i in details_ele.find_all('p')])
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
                else:
                    break

def main():
    HealthCareAsiaMagazine().run()