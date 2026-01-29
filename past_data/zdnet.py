from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, ZDNET_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/zdnet")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

URLS_list = [
    'https://www.zdnet.com/topic/ar-vr/',
    'https://www.zdnet.com/topic/cloud/',
    'https://www.zdnet.com/topic/digital-transformation/',
    'https://www.zdnet.com/topic/energy/',
    'https://www.zdnet.com/topic/energy/',
    'https://www.zdnet.com/topic/robotics/',
    'https://www.zdnet.com/topic/sustainability/',
    'https://www.zdnet.com/topic/transportation/',
    'https://www.zdnet.com/topic/work-life/',
    'https://www.zdnet.com/topic/accelerate-your-tech-game/',
    'https://www.zdnet.com/topic/how-the-new-space-race-will-drive-innovation/',
    'https://www.zdnet.com/topic/how-the-metaverse-will-change-the-future-of-work-and-society/',
    'https://www.zdnet.com/topic/managing-the-multicloud/',
    'https://www.zdnet.com/topic/the-future-of-the-internet/',
    'https://www.zdnet.com/topic/the-tech-trends-to-watch-in-2023/',
    'https://www.zdnet.com/topic/the-new-rules-of-work/',
    'https://www.zdnet.com/topic/amazon/',
    'https://www.zdnet.com/topic/apple/',
    'https://www.zdnet.com/topic/developer/',
    'https://www.zdnet.com/topic/e-commerce/',
    'https://www.zdnet.com/topic/edge-computing/',
    'https://www.zdnet.com/topic/enterprise-software/',
    'https://www.zdnet.com/topic/executive/',
    'https://www.zdnet.com/topic/google/',
    'https://www.zdnet.com/topic/microsoft/',
    'https://www.zdnet.com/topic/professional-development/',
    'https://www.zdnet.com/topic/social-media/',
    'https://www.zdnet.com/topic/smb/',
    'https://www.zdnet.com/topic/windows/',
    'https://www.zdnet.com/topic/how-ai-is-transforming-organizations-everywhere/',
    'https://www.zdnet.com/topic/the-intersection-of-generative-ai-and-engineering/',
    'https://www.zdnet.com/topic/software-development-emerging-trends-and-changing-roles/',
    'https://www.zdnet.com/topic/security/',
    'https://www.zdnet.com/topic/cyber-threats/',
    'https://www.zdnet.com/topic/password-manager/',
    'https://www.zdnet.com/topic/ransomware/',
    'https://www.zdnet.com/topic/vpn/',
    'https://www.zdnet.com/topic/cybersecurity-lets-get-tactical/',
    'https://www.zdnet.com/topic/cybersecurity-lets-get-tactical/',
]
URL = "https://www.zdnet.com/topic/artifiqrafzv@10cial-intelligence/"

class Zdnet:
    def __init__(self):
        self.grid_details = []
        self.page_index = 0
        self.run_loop = True
        self.skipped_urls = 0
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
        main_children = data.find('div',{'class':'c-featureDefaultListing'})
        if not main_children :
            return extracted_data
        
        for children in main_children.find_all('div',{'class':'u-grid-columns'}):

            try:
                tmp = {}
                    
                # link
                link_ele = children.find('a',{'class':'c-listingDefault_itemLink'})
                if link_ele :
                    tmp['url'] = f"https://www.zdnet.com{link_ele.get('href')}"
                    if "https://www.zdnet.com/video/" in tmp['url']:
                        logger.warning('Video article')
                        continue
                    
                author_ele = children.find('a',{'class':'c-listingDefault_author'}) 
                if author_ele :
                    tmp['author'] = author_ele.get_text(strip=True)
                    
                # image
                image_ele = children.find('img')
                if image_ele :
                    tmp['image'] = image_ele.get('src')
                
                    
                # title
                title_ele = children.find('h3')
                if title_ele :
                    tmp['title'] = title_ele.get_text(strip=True)
                
                # # time
                # time_ele = children.find('span',{'class':'c-listingDefault_pubDate'})
                # if time_ele :
                #     tmp['time'] = time_ele.get_text(strip=True)
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
                "time":'',
                "image":""
            }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            video_player_ele = data.find('div',{'class':'c-videoPlayer'})
            if video_player_ele:
                return "Video Article"
            
            # description
            summary_ele = data.find('div',{'class':'c-contentHeader_description'})
            if summary_ele :
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            time_ele = data.find('time',{'class':'c-globalAuthor_time'})
            if time_ele :
                details['time'] = time_ele.get_text(strip=True)
            
            details_ele = data.find('div',{'class':'c-articleContent'})
            if details_ele :
                details['description']['details'] = ' \n'.join([i.get_text(strip=True) for i in details_ele.find_all('p')])
                
                image_ele = details_ele.find('img')
                if image_ele :
                    details['image'] = image_ele.get('src')
                    
        except Exception as e:
            logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
            try:
                
                # if news_details_client.find_one({"url": grid["url"]}):
                    # logger.info(f"Updating (already in DB): {grid['url']}")
                    # self.skipped_urls += 1
                    # continue

                done, response = get_request(f"{grid['url']}")
                if not done:
                    logger.warning(f"Failed fetching: {grid['url']}")
                    continue

                details = self.separate_blog_details(response)
                if not details == "Video Article":
                        
                    merged = {**grid, **details}
                    
                    if not grid['image']:
                        merged['image'] = details['image']
                        
                    merged = {**grid, **details}
                    
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
    Zdnet().run()
    
# if __name__ == "__main__":
#     Zdnet().run()
