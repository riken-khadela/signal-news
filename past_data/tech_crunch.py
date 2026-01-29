import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/main")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URL = "https://techcrunch.com/latest/page/"

class TechCrunch:
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
        
        articles = [ i for i in data.find_all('li',{'class':'post'}) if i.find('img') ]

        now_utc = datetime.now(timezone.utc)
        one_year_ago = now_utc - timedelta(days=365)
        
        extracted_data = []
        for article in articles:
            try:
                article_url = ""
                # Extract title from the span inside the title link
                title_span = article.find('h3')
                if title_span :
                    article_url = title_span.find('a').get('href', '')
                    
                    title = title_span.get_text(strip=True) if title_span else 'No title'
                    if title == 'No title':
                        continue

                # Extract date
                date_span = article.find('time')
                date = date_span.get('datetime', '') if date_span else 'No date'
                article_time = datetime.fromisoformat(
                    date.replace('Z', '+00:00')
                )
                if article_time < one_year_ago:
                    self.run_loop = False
                    continue
                
                # Extract image URL
                img_tag = article.find('img')
                image_url = img_tag.get('src', '') if img_tag else 'No image'
                
                # Extract category (News, etc.)
                category_span = article.find('div', class_='loop-card__cat-group')
                category = category_span.get_text(strip=True) if category_span else 'No category'
                
                # Store the extracted data
                article_data = {
                    'title': title,
                    'url': article_url,
                    'time': date,
                    'image': image_url,
                    'category': category
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
            details['description']['summary'] = data.find('p',{'id':'speakable-summary'}).get_text(strip=True)
            details['description']['details'] = data.find('div',{'class':'wp-block-post-content'}).get_text(strip=True).replace(details['description']['summary'],'')

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
                # Convert time if it's a string
                if isinstance(merged["time"], str) and merged["time"]:
                    try:
                        # TODO: adjust strptime format as per site’s time format
                        merged["time"] = datetime.strptime(
                            merged["time"], "%B %d, %Y"
                        )
                    except Exception:
                        merged["time"] = datetime.utcnow()
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
    TechCrunch().run()
    
# if __name__ == "__main__":
#     TechCrunch().run()
