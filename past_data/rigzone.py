from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
# from settings import get_request, get_scrape_do_requests, NEXT_WEB_client as news_details_client, yourstory_scrape_do_requests
from settings import get_request, get_scrape_do_requests, RIGZONE_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/Azonano")
from datetime import datetime, timedelta, timezone
from bs4 import NavigableString, Tag
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://www.rigzone.com/news/industry_headlines/",
    "https://www.rigzone.com/news/exploration/",
    "https://www.rigzone.com/news/production/",
    "https://www.rigzone.com/news/company_operations/",
    "https://www.rigzone.com/news/finance_and_investing/",
    "https://www.rigzone.com/news/alternative_energy/",
]
BASE_URL = "https://www.rigzone.com/news"

class Azonano:
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
            done, response = get_request(f"{url}")
                
            print(f"{url}")
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
        divs = data.find_all('div',{'class':'smallHeadline'})
        # return [{"url" : 'https://www.rigzone.com/news/wire/usa_is_canceling_almost_30b_in_bidenera_energy_loans-24-jan-2026-182842-article/','time' : 'January 24, 2026','title' : 'USA Is Canceling Almost $30B in Biden-Era Energy Loans Share your comments',"description": {"summary" : "The Trump administration said it's canceling almost $30 billion of financing from the Energy Department's green bank after reviewing transactions approved under former President Joe Biden.","details" : ""}}]
        for blog in divs: 
            try:
                tmp = {
                    "image" : "",
                    "url" : "",
                    "title" : "",
                    "time" : "",
                    "description": {
                        "summary" : "",
                        "details" : ""
                    }
                }

                title_tag = blog.find('a')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                if not title :
                    continue
                
                # link
                link_ele = blog.find('a')
                if link_ele :
                    url = link_ele.get('href') 
                    tmp['url'] =  f"{BASE_URL}{url}" if not BASE_URL in url else url 
                
                # link
                summary_ele = blog.find('div', class_='description')
                if summary_ele :
                    src = summary_ele.get_text(strip=True)
                    tmp['description']['summary'] = src
                    
                if not tmp['url']:
                    continue
                
                
                extracted_data.append(tmp)
                
            except Exception as e:
                print(f"Error extracting data from article: {e}")

        return extracted_data

    def separate_blog_details(self, response, grid):
        """Parse the full blog page for details."""
        details = grid
        try:
            data = BeautifulSoup(response.text, "html.parser")
            content_div = data.find('div', {'id':'content'})
            
            img_ele = content_div.find('img')
            if img_ele :
                details['image'] = img_ele.get('src')
                
            author_ele = data.find('div',{'class':'articleAuthor'}) 
            if author_ele :
                details['author']  = author_ele.get_text(strip=True).replace('by\xa0','').strip()
                
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div',{'id':'divArticleTextForDesktop'})
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
            self.page_index += 1
            self.grid_details = []
            self.get_grid_details(url)
            if self.grid_details:
                self.check_db_grid()


def main():
    Azonano().run()
    