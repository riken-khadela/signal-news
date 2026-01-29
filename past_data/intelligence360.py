from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, intelligence360_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/intelligence360")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URL = "https://www.intelligence360.news/page/"

class Inteligence360:
    def __init__(self):
        self.grid_details = []
        self.page_index = 1
        self.run_loop = True

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0
        self.skipped_urls = 0

    def get_grid_details(self):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(URL + str(self.page_index))
            # done, response = get_scrape_do_requests(URL)
            if not done:
                logger.error(f"Request failed: {URL}")
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
        articles =data.find_all('article')

        now_utc = datetime.now(timezone.utc)
        one_year_ago = now_utc - timedelta(days=365)
        
        extracted_data = []
        for article in articles:
            try:
                article_data = {}
                article_heading = article.find('h2')
                title = article_heading.get_text(strip=True) if article_heading else 'No title'
                article_url = article_heading.find('a').get('href','') if article_heading else ''
                time_tag = article.find('time')
                date = time_tag.get('datetime','') if time_tag else 'No date'
                image_tag = article.find('img')
                image_url = image_tag.get('src','') if image_tag else 'No image'
                author = article.find('span',{'class':'author'}).get_text(strip=True ) if article.find('span',{'class':'author'}) else 'No author'
                
                article_data = {
                    'title': title,
                    'url': article_url,
                    'time': date,
                    'image': image_url,
                    'author': author
                }
                extracted_data.append(article_data)
                
            except Exception as e:
                print(f"Error extracting data from article: {e}")
                continue
        
        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            #  author
            details['author'] = data.find('meta',{'name':'author'}).get('content','')

            # description
            details['description']['summary'] = ""
            details['description']['details'] = '  \n'.join([p.get_text(strip=True) for p in data.find_all('div',{'class':'entry-content'})[0].find_all('p')])

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
        self.page_index = 0
        self.skipped_urls = 0
        
        while True:
            if self.skipped_urls >= 50: break
            #         break
                
            self.page_index += 1
            self.grid_details = []
            self.get_grid_details()
            if self.grid_details:
                self.check_db_grid()

def main():
    Inteligence360().run()
    
# if __name__ == "__main__":
#     Inteligence360().run()
