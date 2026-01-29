import time
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)
from settings import get_request, SACRA_client as news_details_client, get_proxy, random_sleep, get_headers
from logger import CustomLogger

logger = CustomLogger(
    log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/Sacra"
)

BASE_NEWS_URL = "https://sacra.com/explore/companies/"

URLS_LIST = [
    "https://sacra.com/explore/companies/"
]

class Sacra:

    def __init__(self):
        self.grid_details = []
        self.skipped_urls = 0

        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self, BASE_URL = ""):
        if not BASE_URL :
            return
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = uc.Chrome(options=options, version_main=143)
        wait = WebDriverWait(driver,  10)

        try:
            driver.get(BASE_NEWS_URL)
            random_sleep()
            companies_xpath = "//div[contains(@class,'ag-row-level-0')]"
            wait.until(EC.presence_of_element_located((By.XPATH, companies_xpath)))
            companies_urls_li = []
            previous_count = 0
            stale_scrolls = 0
            max_stale_scrolls = 3  
            companies_list= []
            # for _ in range(5):
            while stale_scrolls < max_stale_scrolls:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  
                wait.until(EC.presence_of_element_located((By.XPATH, companies_xpath)))
                
                companies_div = driver.find_elements(By.XPATH, companies_xpath)
                for company in companies_div :
                    tmp = {
                    "image" : "",
                    "url" : "",
                    "title" : "",
                    "description" : {
                        "details" : "",
                        "summary" : ""
                    },
                    'revenue' : {},
                    'growth' : {},
                    'valuation' : {},
                }
                    url_ele = company.find_elements(By.TAG_NAME,'a')
                    if url_ele:
                        tmp['url'] = url_ele[0].get_attribute('href')

                    image_ele = company.find_elements(By.TAG_NAME,'img')
                    if image_ele:
                        tmp['image'] = image_ele[0].get_attribute('src')

                    title_ele = company.find_elements(By.TAG_NAME,'p')
                    if title_ele:
                        tmp['title'] = title_ele[0].text

                    desc_outer_ele = company.find_elements(By.XPATH,"./div[contains(@ col-id,'description')]")
                    if desc_outer_ele :
                        desc_ele = desc_outer_ele[0].find_elements(By.TAG_NAME,'p')
                        if desc_ele:
                            tmp['description']['summary'] = desc_ele[0].text

                    category_outer_ele = company.find_elements(By.XPATH,"./div[contains(@ col-id,'categories')]")
                    if category_outer_ele :
                        category = category_outer_ele[0].find_elements(By.TAG_NAME,'a')
                        if category:
                            tmp['category'] = [ i.text for i in category]

                    revenue_outer_ele = company.find_elements(By.XPATH,"./div[contains(@ col-id,'latest_revenue')]")
                    if revenue_outer_ele :
                        revenue = revenue_outer_ele[0]
                        revenue_list = revenue.text.split('\n')
                        tmp['revenue']['latest_revenue'] = revenue_list[0]
                        if len(revenue_list) > 1 :
                            tmp['revenue']['revenue_year'] = revenue_list[-1]

                    growth_outer_ele = company.find_elements(By.XPATH,"./div[contains(@ col-id,'latest_growth')]")
                    if growth_outer_ele :
                        growth = growth_outer_ele[0]
                        growth_list = growth.text.split('\n')
                        tmp['growth']['latest_growth'] = growth_list[0]
                        if len(growth_list) > 1 :
                            tmp['growth']['growth_year'] = growth_list[-1]

                    valuation_outer_ele = company.find_elements(By.XPATH,"./div[contains(@ col-id,'latest_valuation')]")
                    if valuation_outer_ele :
                        valuation = valuation_outer_ele[0]
                        valuation_list = valuation.text.split('\n')
                        tmp['valuation']['latest_valuation'] = valuation_list[0]
                        if len(valuation_list) > 1 :
                            tmp['valuation']['valuation_year'] = valuation_list[-1]
                    if tmp['url'] not in companies_urls_li:
                        companies_urls_li.append(tmp['url'])
                        companies_list.append(tmp)
                        self.grid_details.append(tmp)

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                next_ele_xpath = "//div[contains(@aria-label,'Next Page')]"
                next_page = driver.find_elements(By.XPATH,next_ele_xpath)
                if next_page:
                    next_page[0].click()

                random_sleep()
                current_count = len(companies_urls_li)
                if current_count == previous_count:
                    stale_scrolls += 1
                else:
                    stale_scrolls = 0
                    
                previous_count = current_count
                print(f"Found {current_count} articles...")

            logger.info(f"Collected {len(self.grid_details)} grid items")

        finally:
            driver.quit()

        return self.grid_details

    def get_article_details(self, slug, grid):

        for _ in range(5):
            random_sleep()
            res = requests.get( grid['url'], headers=get_headers(), proxies=get_proxy(), timeout=15, verify=False,)
            if res.status_code == 200 :
                break
            
        else :
            return grid
        
        data = BeautifulSoup(res.text, 'html.parser')
        body_root_div = data.find('div',{'id':'document_body_root'})
        texts = []
        if body_root_div :
            ALLOWED_TAGS = ["p", "h2", "li"]
            details_ele = data
            if details_ele :
                for tag in body_root_div.find_all(ALLOWED_TAGS, recursive=True):
                    text = tag.get_text(" ", strip=True)
                    if text:
                        texts.append(text)
        grid['description']['details'] = ' \n'.join(texts)
        return grid

    def check_db_grid(self):
        for grid in self.grid_details:
            for _ in range(3):
                try:
                    # if news_details_client.find_one({"url": grid["url"]}):
                        # self.skipped_urls += 1
                        # continue

                    slug = grid["url"].rstrip("/").split("/")[-1]

                    details = self.get_article_details(slug, grid)
                    if not details:
                        continue

                    merged = {**grid, **details}
                    if not merged.get('description',{}).get('details','') :
                        continue
                    merged['created_at'] = ist_time
                    
                    news_details_client.update_one( 
                        {"url": merged["url"]},
                        {"$set": merged},
                        upsert=True,
                    )

                    logger.info(f"Inserted: {merged['url']}")
                    time.sleep(1)
                    break

                except Exception as e:
                    logger.error(f"Insert error: {e} in url : {grid['url']}")

    def run(self):
        for url in URLS_LIST:
            self.get_grid_details(url)
            if self.grid_details:
                self.check_db_grid()


def main():
    Sacra().run()
