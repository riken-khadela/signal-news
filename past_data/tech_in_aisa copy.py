from driver_bot import BOT, BotConfig
from selenium.webdriver.common.by import By
import time
import os
import time
import random
import json
import logging
from typing import Optional, List, Tuple, Any, Callable
from functools import wraps
from contextlib import contextmanager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    WebDriverException,
    ElementClickInterceptedException
)
import undetected_chromedriver as uc

import logging
import time
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, TECH_IN_ASIA_client as news_details_client, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/NEXT_WEB")
from datetime import datetime, timedelta, timezone
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

from datetime import datetime, timedelta, timezone

URLS_list = [
    "https://www.techinasia.com/news"
]

def get_grid_data(URLS_list):
    
    options = uc.ChromeOptions()
    options.add_argument('--headless')  
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = None
    all_data = []
    
    try:
        driver = uc.Chrome(options=options, version_main=143)
        wait = WebDriverWait(driver, 10)
        
        for url in URLS_list:
            print(f"Scraping: {url}")
            driver.get(url)
            
            try:
                wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//article[contains(@class,'post-card')]")
                ))
            except TimeoutException:
                print(f"No articles found on {url}")
                continue
            
            previous_count = 0
            stale_scrolls = 0
            max_stale_scrolls = 3  
            
            # while stale_scrolls < max_stale_scrolls:
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) 
                
                current_count = len(driver.find_elements(
                    By.XPATH, "//article[contains(@class,'post-card')]"
                ))
                
                if current_count == previous_count:
                    stale_scrolls += 1
                else:
                    stale_scrolls = 0
                    
                previous_count = current_count
                print(f"Found {current_count} articles...")

            articles = driver.find_elements(By.XPATH, "//article[contains(@class,'post-card')]")
            articles_grid_data = []
            
            for idx, article in enumerate(articles):
                try:
                    tmp = {}
                    
                    try:
                        tmp['title'] = article.find_element(By.TAG_NAME, 'h3').text
                    except NoSuchElementException:
                        tmp['title'] = None
                    
                    try:
                        tmp['image'] = article.find_element(By.TAG_NAME, 'img').get_attribute('src')
                    except NoSuchElementException:
                        tmp['image'] = None
                    
                    try:
                        post_img = article.find_element(By.XPATH,"//div[contains(@class,'post-image')]")
                        if not post_img :
                            logger.info('No post image')
                            continue
                        
                        tmp['url'] = post_img.find_element(By.TAG_NAME, "a").get_attribute('href')
                    except NoSuchElementException:
                        tmp['url'] = None
                    
                    try:
                        tmp['time'] = article.find_element(By.TAG_NAME, 'time').get_attribute('datetime')
                    except NoSuchElementException:
                        tmp['time'] = None
                    
                    all_data.append(tmp)
                    
                except Exception as e:
                    print(f"Error extracting article {idx}: {str(e)}")
                    continue
            
            print(f"Scraped {len(articles_grid_data)} articles from {url}")
            
    except Exception as e:
        print(f"Critical error: {str(e)}")
        raise
        
    finally:
        if driver:
            driver.quit()
    
    return all_data


class TechCrunch:
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


    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {
            "description": {
                    "summary" : "",
                    "details" : ""
                },
                "time":'',
            }
        try:
            breakpoint()
            data = BeautifulSoup(response.text, "html.parser")
            
            main_article = data.find('div',{'class':'c-articles'})
            data.find('div',{'id':'content'})
            if not main_article:
                logger.warning(f"Could not find main article container")
                return details
            
            # description
            summary_ele = main_article.find('p',{'class':'c-header__intro'})
            if summary_ele :
                details['description']['summary'] = summary_ele.get_text(strip=True)
            
            time_ele = main_article.find('time')
            if time_ele :
                details['time'] = time_ele.get_text(strip=True)
            
            ALLOWED_TAGS = ["p", "h3"]
            details_ele = main_article.find('div',{'id':'article-main-content'})
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
                
                breakpoint()
                
                done, response = get_request(grid['url'])
                if not done:
                    logger.warning(f"Failed fetching: {grid['url']}")
                    continue
                
                
                details = self.separate_blog_details(response)
                merged = {**grid, **details}
                
                if not merged['time']:
                    breakpoint()
                    logger.warning(f"Failed fetching TIME: {grid['url']}")
                if not merged['title']:
                    breakpoint()
                    logger.warning(f"Failed fetching title: {grid['url']}")
                if not merged['image']:
                    breakpoint()
                    logger.warning(f"Failed fetching image: {grid['url']}")
                    
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
        self.grid_details = get_grid_data(URLS_list)
        if self.grid_details:
            self.check_db_grid()

def main():
    TechCrunch().run()
    
# if __name__ == "__main__":
#     TechCrunch().run()
