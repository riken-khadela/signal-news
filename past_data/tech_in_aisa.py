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

from settings import get_request, TECHINASIA_client as news_details_client, get_proxy, random_sleep
from logger import CustomLogger

logger = CustomLogger(
    log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/TechInAsia"
)

BASE_NEWS_URL = "https://www.techinasia.com/news"
API_BASE = "https://www.techinasia.com/gateway-api-express/techinasia/1.0/posts/"

JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczpcL1wvd3d3LnRlY2hpbmFzaWEuY29tIiwic3ViIjoiMTQwMjc1MSIsImF1ZCI6Imh0dHBzOlwvXC93d3cudGVjaGluYXNpYS5jb20iLCJleHAiOjE4MDA2OTYxMDksIm5iZiI6MTc2OTE2MDA0OSwiaWF0IjoxNzY5MTYwMTA5LCJqdGkiOiI0ZjY5YjNkMjM3N2E4MjRhMTU1N2I2YjdlMWM3M2MzNGMyMjlhYjNiOGJlOWNkNmQzYWRjYzI1YjJhOTAxODQ3IiwiZGF0YSI6eyJzZXNzaW9uX2lkIjoiNGY2OWIzZDIzNzdhODI0YTE1NTdiNmI3ZTFjNzNjMzRjMjI5YWIzYjhiZTljZDZkM2FkY2MyNWIyYTkwMTg0NyIsImlkX3RlY2hpbmFzaWEiOiIxNDAyNzUxIiwiaWRfdGVjaGxpc3QiOiI2ZDAzNjcwNy0zNDM4LTQ3NzctOTJhNC05NjA3YmYwZTFiNDciLCJlbWFpbCI6InJpa2Vua2hhZGVsYTc3N0BnbWFpbC5jb20iLCJmaXJzdF9uYW1lIjoiUmlrZW4iLCJsYXN0X25hbWUiOiJLaGFkZWxhIiwic2x1ZyI6InJpa2VuLWtoYWRlbGEiLCJyZWdpc3RlcmVkX2RhdGUiOiIyMDI2LTAxLTIzVDA5OjAwOjAzKzAwOjAwIiwiaXAiOiIxNTIuNTkuMzYuOTIiLCJhdmF0YXJfdXJsIjoiaHR0cHM6XC9cL3N0YXRpYy50ZWNoaW5hc2lhLmNvbVwvYXNzZXRzXC9pY29uLWRlZmF1bHRwcm9maWxlLnBuZyIsImF1dGhvcl91cmwiOiJodHRwczpcL1wvd3d3LnRlY2hpbmFzaWEuY29tXC9wcm9maWxlXC9yaWtlbi1raGFkZWxhIn19.oL2h8HlHRLmm2KPf6VmScd75ZPtcyBQkBeHtWqqL790"

HEADERS = {
    "accept": "*/*",
    "authorization": f"Bearer {JWT_TOKEN}",
    "user-agent": "Mozilla/5.0",
    "referer": BASE_NEWS_URL,
}
headers = { 'accept': '*/*',   'accept-language': 'en,gu;q=0.9', 'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczpcL1wvd3d3LnRlY2hpbmFzaWEuY29tIiwic3ViIjoiMTQwMjc1MSIsImF1ZCI6Imh0dHBzOlwvXC93d3cudGVjaGluYXNpYS5jb20iLCJleHAiOjE4MDA2OTYxMDksIm5iZiI6MTc2OTE2MDA0OSwiaWF0IjoxNzY5MTYwMTA5LCJqdGkiOiI0ZjY5YjNkMjM3N2E4MjRhMTU1N2I2YjdlMWM3M2MzNGMyMjlhYjNiOGJlOWNkNmQzYWRjYzI1YjJhOTAxODQ3IiwiZGF0YSI6eyJzZXNzaW9uX2lkIjoiNGY2OWIzZDIzNzdhODI0YTE1NTdiNmI3ZTFjNzNjMzRjMjI5YWIzYjhiZTljZDZkM2FkY2MyNWIyYTkwMTg0NyIsImlkX3RlY2hpbmFzaWEiOiIxNDAyNzUxIiwiaWRfdGVjaGxpc3QiOiI2ZDAzNjcwNy0zNDM4LTQ3NzctOTJhNC05NjA3YmYwZTFiNDciLCJlbWFpbCI6InJpa2Vua2hhZGVsYTc3N0BnbWFpbC5jb20iLCJmaXJzdF9uYW1lIjoiUmlrZW4iLCJsYXN0X25hbWUiOiJLaGFkZWxhIiwic2x1ZyI6InJpa2VuLWtoYWRlbGEiLCJyZWdpc3RlcmVkX2RhdGUiOiIyMDI2LTAxLTIzVDA5OjAwOjAzKzAwOjAwIiwiaXAiOiIxNTIuNTkuMzYuOTIiLCJhdmF0YXJfdXJsIjoiaHR0cHM6XC9cL3N0YXRpYy50ZWNoaW5hc2lhLmNvbVwvYXNzZXRzXC9pY29uLWRlZmF1bHRwcm9maWxlLnBuZyIsImF1dGhvcl91cmwiOiJodHRwczpcL1wvd3d3LnRlY2hpbmFzaWEuY29tXC9wcm9maWxlXC9yaWtlbi1raGFkZWxhIn19.oL2h8HlHRLmm2KPf6VmScd75ZPtcyBQkBeHtWqqL790', 'priority': 'u=1, i', 'referer': 'https://www.techinasia.com/news/spacex-in-talks-with-wall-street-banks-on-potential-ipo-report', 'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Linux"', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin', 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36', }

URLS_LIST = [
    "https://www.techinasia.com/news?category=all",
    "https://www.techinasia.com/news?category=artificial-intelligence",
    "https://www.techinasia.com/news?category=e-commerce-social-commerce",
    "https://www.techinasia.com/news?category=fintech",
    "https://www.techinasia.com/news?category=crypto",
    "https://www.techinasia.com/news?category=investments",
    "https://www.techinasia.com/news?category=china",
    "https://www.techinasia.com/news?category=india",
    "https://www.techinasia.com/news?category=south-east-asia"
]

class TechInAsia:

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
        # options.add_argument(f'--proxy-server={get_proxy()["http"]}')

        driver = uc.Chrome(options=options, version_main=143)
        wait = WebDriverWait(driver,  10)

        try:
            driver.get(BASE_NEWS_URL)

            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//article[contains(@class,'post-card')]")
                )
            )

            previous_count = 0
            stale_scrolls = 0
            max_stale_scrolls = 3  
            
            # for _ in range(2):
            while stale_scrolls < max_stale_scrolls:
                
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

            articles = driver.find_elements(
                By.XPATH, "//article[contains(@class,'post-card')]"
            )

            for article in articles:
                try:
                    tmp = {
                        "title": "",
                        "url": "",
                        "image": "",
                        "time": "",
                    }

                    try:
                        tmp["title"] = article.find_element(By.TAG_NAME, "h3").text
                    except NoSuchElementException:
                        continue

                    try:
                        tmp["image"] = article.find_element(By.TAG_NAME, "img").get_attribute("src")
                    except NoSuchElementException:
                        pass

                    try:
                        tmp["url"] = article.find_element(
                            By.XPATH, ".//a[contains(@href,'/news/')]"
                        ).get_attribute("href")
                    except NoSuchElementException:
                        continue

                    try:
                        tmp["time"] = article.find_element(
                            By.TAG_NAME, "time"
                        ).get_attribute("datetime")
                    except NoSuchElementException:
                        pass

                    self.grid_details.append(tmp)

                except Exception as e:
                    logger.warning(f"Grid parse error: {e}")

            logger.info(f"Collected {len(self.grid_details)} grid items")

        finally:
            driver.quit()

        return self.grid_details

    def get_article_details(self, slug):
        url = f"{API_BASE}{slug}"
        for _ in range(5):
            random_sleep()
            res = requests.get( url, headers=headers, proxies=get_proxy(), timeout=15, verify=False,)
            if res.status_code == 200 :
                break
            
        else :
            return {
                "author": "",
                "time": "",
                "description": {
                    "summary": "",
                    "details":  "",
                },
            }
        posts = res.json().get("posts",[])
        post = {}
        content = ""
        texts = []
        if posts :
            post = posts[0]
            content = post.get('content',"")
            if content:
                data = BeautifulSoup(content, 'html.parser')
                
                ALLOWED_TAGS = ["p", "h2", "li"]
                details_ele = data
                if details_ele :
                    for tag in details_ele.find_all(ALLOWED_TAGS, recursive=True):
                        text = tag.get_text(" ", strip=True)
                        if text:
                            texts.append(text)
        
        return {
            "author": post.get("author",{}).get('display_name',''),
            "time": post.get("date_gmt"),
            "image" : post.get('featured_image',{}).get('source',''),
            "description": {
                "summary": "",
                "details":  ' \n'.join(texts),
            },
        }

    def check_db_grid(self):
        for grid in self.grid_details:
            for _ in range(3):
                try:
                    # if news_details_client.find_one({"url": grid["url"]}):
                        # self.skipped_urls += 1
                        # continue

                    slug = grid["url"].rstrip("/").split("/")[-1]

                    details = self.get_article_details(slug)
                    if not details:
                        continue

                    merged = {**grid, **details}
                    if not merged.get('description',{}).get('details','') :
                        continue
                    
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
        breakpoint()
        for url in URLS_LIST:
            self.get_grid_details(url)
            if self.grid_details:
                self.check_db_grid()


def main():
    TechInAsia().run()