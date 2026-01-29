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

from settings import get_request, TECHINASIA_client as news_details_client, get_proxy, random_sleep, parse_datetime_safe
from base_scraper import BaseScraper
from logger import CustomLogger

# UNIQUE: Selenium-based scraper with API integration
BASE_NEWS_URL = "https://www.techinasia.com/news"
API_BASE = "https://www.techinasia.com/gateway-api-express/techinasia/1.0/posts/"

# UNIQUE: JWT token for API authentication
JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczpcL1wvd3d3LnRlY2hpbmFzaWEuY29tIiwic3ViIjoiMTQwMjc1MSIsImF1ZCI6Imh0dHBzOlwvXC93d3cudGVjaGluYXNpYS5jb20iLCJleHAiOjE4MDA2OTYxMDksIm5iZiI6MTc2OTE2MDA0OSwiaWF0IjoxNzY5MTYwMTA5LCJqdGkiOiI0ZjY5YjNkMjM3N2E4MjRhMTU1N2I2YjdlMWM3M2MzNGMyMjlhYjNiOGJlOWNkNmQzYWRjYzI1YjJhOTAxODQ3IiwiZGF0YSI6eyJzZXNzaW9uX2lkIjoiNGY2OWIzZDIzNzdhODI0YTE1NTdiNmI3ZTFjNzNjMzRjMjI5YWIzYjhiZTljZDZkM2FkY2MyNWIyYTkwMTg0NyIsImlkX3RlY2hpbmFzaWEiOiIxNDAyNzUxIiwiaWRfdGVjaGxpc3QiOiI2ZDAzNjcwNy0zNDM4LTQ3NzctOTJhNC05NjA3YmYwZTFiNDciLCJlbWFpbCI6InJpa2Vua2hhZGVsYTc3N0BnbWFpbC5jb20iLCJmaXJzdF9uYW1lIjoiUmlrZW4iLCJsYXN0X25hbWUiOiJLaGFkZWxhIiwic2x1ZyI6InJpa2VuLWtoYWRlbGEiLCJyZWdpc3RlcmVkX2RhdGUiOiIyMDI2LTAxLTIzVDA5OjAwOjAzKzAwOjAwIiwiaXAiOiIxNTIuNTkuMzYuOTIiLCJhdmF0YXJfdXJsIjoiaHR0cHM6XC9cL3N0YXRpYy50ZWNoaW5hc2lhLmNvbVwvYXNzZXRzXC9pY29uLWRlZmF1bHRwcm9maWxlLnBuZyIsImF1dGhvcl91cmwiOiJodHRwczpcL1wvd3d3LnRlY2hpbmFzaWEuY29tXC9wcm9maWxlXC9yaWtlbi1raGFkZWxhIn19.oL2h8HlHRLmm2KPf6VmScd75ZPtcyBQkBeHtWqqL790"

HEADERS = {
    "accept": "*/*",
    "authorization": f"Bearer {JWT_TOKEN}",
    "user-agent": "Mozilla/5.0",
    "referer": BASE_NEWS_URL,
}

headers = {
    'accept': '*/*',
    'accept-language': 'en,gu;q=0.9',
    'authorization': f'Bearer {JWT_TOKEN}',
    'priority': 'u=1, i',
    'referer': 'https://www.techinasia.com/news/spacex-in-talks-with-wall-street-banks-on-potential-ipo-report',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
}

# UNIQUE: Multiple category URLs
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

class TechInAsia(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/tech_in_aisa"
        )
        self.grid_details = []

    def get_grid_details(self, BASE_URL=""):
        """UNIQUE: Selenium-based grid scraping with infinite scroll"""
        if not BASE_URL:
            return
        
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = uc.Chrome(options=options, version_main=143)
        wait = WebDriverWait(driver, 10)

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
            
            # UNIQUE: Infinite scroll with stale detection
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
                self.logger.info(f"Found {current_count} articles...")

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

                    # Check if exists (with skip tracking)
                    if self.check_article_exists(tmp["url"]):
                        continue

                    try:
                        tmp["time"] = parse_datetime_safe(article.find_element(
                            By.TAG_NAME, "time"
                        ).get_attribute("datetime"))
                    except NoSuchElementException:
                        pass

                    self.grid_details.append(tmp)

                except Exception as e:
                    self.logger.warning(f"Grid parse error: {e}")

            self.logger.info(f"Collected {len(self.grid_details)} grid items")

        finally:
            driver.quit()

        return self.grid_details

    def get_article_details(self, slug):
        """UNIQUE: Fetch article details from API"""
        url = f"{API_BASE}{slug}"
        for _ in range(5):
            random_sleep()
            res = requests.get(url, headers=headers, proxies=get_proxy(), timeout=15, verify=False)
            if res.status_code == 200:
                break
        else:
            return {
                "author": "",
                "time": "",
                "description": {
                    "summary": "",
                    "details": "",
                },
            }
        
        posts = res.json().get("posts", [])
        post = {}
        content = ""
        texts = []
        
        if posts:
            post = posts[0]
            content = post.get('content', "")
            if content:
                data = BeautifulSoup(content, 'html.parser')
                
                ALLOWED_TAGS = ["p", "h2", "li"]
                for tag in data.find_all(ALLOWED_TAGS, recursive=True):
                    text = tag.get_text(" ", strip=True)
                    if text:
                        texts.append(text)
        
        return {
            "author": post.get("author", {}).get('display_name', ''),
            "time": parse_datetime_safe(post.get("date_gmt")),
            "image": post.get('featured_image', {}).get('source', ''),
            "description": {
                "summary": "",
                "details": ' \n'.join(texts),
            },
        }

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
            for _ in range(3):
                try:
                    slug = grid["url"].rstrip("/").split("/")[-1]

                    details = self.get_article_details(slug)
                    if not details:
                        continue

                    merged = {**grid, **details}
                    if not merged.get('description', {}).get('details', ''):
                        continue
                    
                    merged['created_at'] = datetime.now()
                    
                    # Use save_article from BaseScraper
                    if self.save_article(merged):
                        self.logger.info(f"✅ Saved: {merged['url']}")

                    time.sleep(1)
                    break

                except Exception as e:
                    self.logger.error(f"Insert error: {e} in url : {grid['url']}")

    def run(self):
        """Main execution logic - UNIQUE: Selenium + API integration"""
        self.logger.info("🚀 Starting Tech In Asia scraper (Selenium + API)")
        
        for url in URLS_LIST:
            self.logger.info(f"📂 Processing category: {url}")
            self.get_grid_details(url)
            if self.grid_details:
                self.check_db_grid()
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ Tech In Asia scraper completed")

def main():
    TechInAsia().run()
    
if __name__ == "__main__":
    main()