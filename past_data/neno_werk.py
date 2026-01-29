from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
# from settings import get_request, get_scrape_do_requests, NEXT_WEB_client as news_details_client, yourstory_scrape_do_requests
from settings import get_request, get_scrape_do_requests, NANOWERK_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/NanoWerk")
from datetime import datetime, timedelta, timezone
from bs4 import NavigableString, Tag
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    "https://www.nanowerk.com/category-nanoresearch.php?page="
]
BASE_URL = "https://www.mining.com/"

class NanoWerk:
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
            done, response = get_request(f"{url + str(self.page_index)}/")
                
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
        section = data.find('section', class_='articles')
        divs = section.find_all('div', recursive=False)

        for blog in divs: 
            try:
                tmp = {
                    "image" : "",
                    "url" : "",
                    "title" : "",
                    "time" : ""
                }

                title_tag = blog.find('h2')
                title = title_tag.get_text(strip=True) if title_tag else ""
                tmp['title'] = title
                
                # link
                link_ele = blog.find('a')
                if link_ele :
                    url = link_ele.get('href')
                    tmp['url'] =  url
                
                # link
                img_ele = blog.find('img')
                if img_ele :
                    src = img_ele.get('src')
                    tmp['image'] = src
                    
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
                },
            "author" : ""
            }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            time_ele = data.find('meta',{'property':'article:published_time'}) 
            if time_ele :
                details['time'] = time_ele.get('content')
                
            author_ele = data.find('script',{'type':'application/ld+json'}) 
            if author_ele :
                author_list = json.loads(author_ele.get_text(strip=True))
                if 'author' in author_list.keys():
                    if type(author_list['author']) == list :
                        author = author_list['author'][0].get('name',"")
                    else:
                        author = author_list['author'].get('name',"")
                        
                    details['author'] = author
                
            summary_ele = data.find('meta',{'property':'og:description'}) 
            if summary_ele :
                details['summary'] = summary_ele.get('content')
            
            allowed_tags = {"em"}
            clean_tds = []
            for td in data.find_all("td"):
                valid = True

                for child in td.contents:
                    if isinstance(child, NavigableString):
                        continue
                    elif isinstance(child, Tag) and child.name in allowed_tags:
                        continue
                    else:
                        valid = False
                        break

                if valid:
                    text = td.get_text(strip=True)
                    if text:
                        clean_tds.append(text)
            details['description']['details'] = '\n'.join(clean_tds)
            
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
    NanoWerk().run()

# if __name__ == "__main__":
#     NanoWerk().run()
