import time
import json, random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from settings import get_request, news_details_client
from logger import CustomLogger
import requests

logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/past_data/Logs/main")
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

AJAX_URL = "https://techfundingnews.com/wp-json/csco/v1/more-posts"

HEADERS = {
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://techfundingnews.com",
    "user-agent": "Mozilla/5.0",
    "x-requested-with": "XMLHttpRequest",
}

ONE_YEAR_AGO = datetime.utcnow() - timedelta(days=365)

CATEGORIES = {
    "acquisition": {"url": "https://techfundingnews.com/category/acquisition/", "cat_id": 82},
    "top-funding-rounds": {"url": "https://techfundingnews.com/category/top-funding-rounds/", "cat_id": 83},
}


PROXIES = [
    "37.48.118.90:13082",
    "83.149.70.159:13082",
    "163.172.59.195:15003",
    "163.172.26.179:15003",
    "163.172.48.119:15003",
    "51.15.2.19:15003",
    "163.172.59.195:15004",
    "163.172.26.179:15004",
    "163.172.48.119:15004",
    "51.15.2.19:15004",
    "51.159.35.167:15003",
    "163.172.84.215:15003",
    "163.172.251.67:15003",
    "163.172.43.22:15003",
    "51.159.35.167:15004",
    "163.172.84.215:15004",
    "163.172.251.67:15004",
    "163.172.43.22:15004",
    "63.141.241.98:16001",
    "173.208.209.42:16001",
    "142.54.188.26:16001",
    "173.208.199.74:16001",
    "163.172.58.253:16001",
    "163.172.61.67:16001",
    "51.159.4.90:16001",
    "163.172.71.115:16001",
]
OPTIONS = {
    "location": "archive",
    "meta": "archive_post_meta",
    "layout": "list",
}

def get_proxy():
    prx = random.choice(PROXIES)
    return {"http": f"http://{prx}", "https": f"http://{prx}"}

class TechFundingNews:

    def __init__(self):
        self.grid_details = []
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    # ----------------------------------------------------
    # DATE PARSER (REAL DATE SOURCE)
    # ----------------------------------------------------
    def parse_date(self, article):
        date_div = article.find("div", class_="cs-meta-date")
        if not date_div:
            return None
        try:
            return datetime.strptime(date_div.get_text(strip=True), "%B %d, %Y")
        except Exception:
            return None

    # ----------------------------------------------------
    # AJAX PAGE FETCH
    # ----------------------------------------------------
    
    def get_request(self, url):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return True, r
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return False, None
        
    def fetch_page(self, category_name, cat_id, page, max_retries=20, timeout=10):
        payload = {
            "action": "csco_ajax_load_more",
            "page": page,
            "posts_per_page": 9,
            "query_data": json.dumps({
                "query_vars": {
                    "category_name": category_name,
                    "cat": cat_id,
                    "posts_per_page": 9,
                    "order": "DESC"
                },
                "is_archive": True,
                "is_category": True,
                "infinite_load": False,
            }),
            "attributes": "false",
            "options": json.dumps(OPTIONS),
        }

        for attempt in range(max_retries):
            try:
                r = requests.post(AJAX_URL, headers=HEADERS, data=payload, timeout=timeout, proxies=get_proxy())
                r.raise_for_status()
                return r.json().get("data", {}).get("content", "")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {category_name} page {page}: {e}")
                time.sleep(2) 
                
        return None

    # ----------------------------------------------------
    # GRID PARSER
    # ----------------------------------------------------
    def scrape_grid_html(self, html, category_name):
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.find_all("article"):
            try:
                published = self.parse_date(article)
                if not published:
                    continue

                # ⛔ STOP when older than 1 year
                if published < ONE_YEAR_AGO:
                    return True

                title_tag = article.find("h2").find("a")
                img = article.find("img")

                categories = article.find("div", class_="cs-meta-category")
                category_text = ", ".join([i.text for i in categories.find_all("li")]) if categories else category_name

                self.grid_details.append({
                    "title": title_tag.get_text(strip=True),
                    "url": title_tag["href"],
                    "time": published,
                    "image": img.get("data-pk-src") if img else "",
                    "category": category_text
                })

            except Exception:
                continue

        return False

    # ----------------------------------------------------
    # FULL BLOG PARSER
    # ----------------------------------------------------
    def separate_blog_details(self, response):
        data = BeautifulSoup(response.text, "html.parser")
        return {
            "author": data.find("meta", {"name": "author"}).get("content", ""),
            "description": {
                "details": data.find("div", class_="entry-content").get_text(strip=True)
            }
        }

    # ----------------------------------------------------
    # SAVE TO DB
    # ----------------------------------------------------
    def save_to_db(self):
        for grid in self.grid_details:
            # if news_details_client.find_one({"url": grid["url"]}):
                # continue

            done, response = get_request(grid["url"])
            if not done:
                continue

            details = self.separate_blog_details(response)
            merged = {**grid, **details}
                
            news_details_client.update_one(
                {"url": merged["url"]},
                {"$set": merged},
                upsert=True
            )
            logger.info(f"Saved: {grid['url']}")
            time.sleep(1)

    # ----------------------------------------------------
    # RUN
    # ----------------------------------------------------
    def run(self):
        for cat_name, cfg in CATEGORIES.items():
            page = 1
            logger.info(f"Scraping category: {cat_name}")

            while True:
                html = self.fetch_page(cat_name, cfg["cat_id"], page)
                if not html.strip():
                    break

                stop = self.scrape_grid_html(html, cat_name)
                if stop:
                    break

                page += 1
                time.sleep(1)

        self.save_to_db()
        
def main():
    TechFundingNews().run()
    
# if __name__ == "__main__":
#     scraper = TechFundingNews()
#     scraper.run()