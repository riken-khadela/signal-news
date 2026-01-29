from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, BUSINESSINSIDER_client as news_details_client, yourstory_scrape_do_requests, is_date_between_year_and_today
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/businessinsider")
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    'https://www.businessinsider.com/strategy'
]
BASE_URL = "https://www.businessinsider.com"
API_BASE_URL = "https://www.businessinsider.com/ajax/content-api/vertical?templateId=legacy-river&capiVer=2&riverSize=50&riverNextPageToken="
class BusinessInsider:
    def __init__(self):
        self.grid_details = []
        self.page_index = 0
        self.run_loop = True
        self.next_url = ""

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            # done, response = get_request(url + str(self.page_index))
            done, response = get_request(url)
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

    

    def extract_best_image(self,img_tag):
        if not img_tag:
            return None

        data_srcs = img_tag.get("data-srcs")
        if data_srcs:
            try:
                src_map = json.loads(data_srcs)
                return max(
                    src_map.keys(),
                    key=lambda k: src_map[k].get("aspectRatioW", 0)
                )
            except Exception:
                pass

        noscript = img_tag.find_next("noscript")
        if noscript:
            fallback = noscript.find("img")
            if fallback and fallback.get("src"):
                return fallback["src"]

        return None


    def parse_articles(self,rendered_html, category):
        soup = BeautifulSoup(rendered_html, "lxml")
        articles = []

        for node in soup.select("article[data-component-type='tout']"):
            title_el = node.select_one("h3.tout-title a")
            img_el = node.select_one("img.lazy-image")
            summary_el = node.select_one(".tout-copy")
            read_time_el = node.select_one(".tout-read-time")

            if not title_el:
                continue

            articles.append({
                "category": category,
                "title": title_el.get_text(strip=True),
                "url": urljoin(BASE_URL, title_el.get("href")),
                "image": self.extract_best_image(img_el),
                "summary": summary_el.get_text(strip=True) if summary_el else None,
                "read_time": read_time_el.get_text(strip=True) if read_time_el else None,
            })

        return articles
    
    def scrape_grid_data(self, html_content):
        """
        Extract article data from YourStory search results
        """
        
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        category = "strategy"
        self.next_url = API_BASE_URL+data.find_all('div',{'class':'sub-vertical'})[-1].get('data-next').split('Token=')[-1]+f"&id={category}"
        articles_list = self.parse_articles(html_content, category)
        extracted_data.extend(articles_list)
        self.check_db_grid(articles_list)
        # for _ in range(4):
        while True :
            try :
                done, response = get_request(self.next_url)
                if not done :
                    continue
                    
                payload = response.json()
                block = payload.get(category, {})
                rendered_html = block.get("rendered")
                articles_list = self.parse_articles(rendered_html, category)
                self.check_db_grid(articles_list)
                extracted_data.extend(articles_list)
                if payload[category]['links'] == {}:
                    break
                
                self.next_url = API_BASE_URL+payload[category]['links']['next'].split('Token=')[-1]+f"&id={category}"
                
                pass
            except Exception as e:
                print(e)
        
        return extracted_data
    
    

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {},"time":'',"author" : ""}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            author = data.find("a", {"class": "byline-author-name"})
            details['author'] = author.get_text(strip=True) if author else ""

            time_ele = data.find('time')
            if time_ele:
                details['time'] = time_ele.get('data-timestamp')

            summary_ele = data.find('div',{'class':'post-summary-bullets'})
            if summary_ele :
                details['description']['summary'] = ' \n'.join([i.get_text(strip=True) for i in summary_ele.find_all('li')])
            
            ALLOWED_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6"]
            details_ele = data.find('section',{'class':'post-story-body-content'})
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

    def check_db_grid(self, articles_list = []):
        """Check DB before fetching details; skip if exists."""
        if not articles_list :
            articles_list = self.grid_details
            
        for grid in articles_list:
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
                if details == False:
                    continue
                
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
    BusinessInsider().run()
    
