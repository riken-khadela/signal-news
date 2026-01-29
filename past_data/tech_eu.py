from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, TECH_EU_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import re
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/NEXT_WEB")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://tech.eu/page/"
]


def parse_relative_time(text: str) -> datetime | None:
    """Parse relative time strings like '2 hours ago'."""
    text = text.lower().strip()
    now = datetime.now(timezone.utc)

    if text in {"just now", "now"}:
        return now

    match = re.match(r'(\d+)\s+(minute|min|hour|day|week|month|year)s?(?:\s+ago)?', text)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)

    if unit.startswith("min"):
        return now - timedelta(minutes=value)
    if unit.startswith("hour"):
        return now - timedelta(hours=value)
    if unit.startswith("day"):
        return now - timedelta(days=value)
    if unit.startswith("week"):
        return now - timedelta(weeks=value)
    if unit.startswith("month"):
        return now - relativedelta(months=value)
    if unit.startswith("year"):
        return now - relativedelta(years=value)

    return None

def parse_absolute_date(text: str) -> datetime | None:
    """Parse absolute dates like '01 December 2025'."""
    formats = [
        "%d %B %Y",
        "%B %d, %Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

def parse_time(text: str) -> datetime | None:
    """Try parsing as relative time first, then absolute date."""
    result = parse_relative_time(text)
    if result is not None:
        return result
    return parse_absolute_date(text)

class TechEu:
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
        
        main_children = data.find_all('div',{'class':'post-card'})
        if not main_children :
            return extracted_data
        
        
        for children in main_children:

            try:
                tmp = {
                        "title": "",
                        "author": "",
                        "image": "",
                    }
                author_ele = children.find('a',{'class':"post-author-name"}) 
                if author_ele :
                    tmp['author'] = author_ele.get_text(strip=True)
                    
                image_ele = children.find('img') 
                if image_ele :
                    tmp['image'] = image_ele.get('data-srcset').split(',')[-1].strip().split(' ')[0].strip()
                    
                # title
                title_ele = children.find('div',{'class':'post-title'})
                if title_ele :
                    tmp['title'] = title_ele.get_text(strip=True)
                    
                    # link
                    link_ele = title_ele.find('a')
                    if link_ele :
                        url = link_ele.get('href')
                        tmp['url'] = url
                        
                if not tmp['url']:
                    continue
                
                extracted_data.append(tmp)
                
            except Exception as e:
                print(f"Error extracting data from article: {e}")

        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {},"time":''}
        details = {
            "description" : {
                "summary" : "",
                "details" : ""
            }
        }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # description
            summary_ele = data.find('div',{'class':'single-post-summary'})
            if summary_ele :
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            time_ele = data.find('span',{'class':'sp-date'})
            if time_ele :
                details['time'] = parse_time(time_ele.get_text(strip=True))
            
            ALLOWED_TAGS = ["p", "h2"]
            details_ele = data.find('div',{'class':'single-post-content'})
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
            while self.run_loop:
                self.page_index += 1
                self.grid_details = []
                self.get_grid_details(url)
                if self.grid_details:
                    self.check_db_grid()

def main():
    TechEu().run()
    
# if __name__ == "__main__":
#     TechEu().run()
