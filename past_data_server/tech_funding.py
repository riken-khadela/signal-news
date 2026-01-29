import time
import json, random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from settings import get_request, news_details_client
from base_scraper import BaseScraper
from logger import CustomLogger
import requests
import pytz

ist = pytz.timezone("Asia/Kolkata")

# UNIQUE: Custom AJAX API endpoint
AJAX_URL = "https://techfundingnews.com/wp-json/csco/v1/more-posts"

HEADERS = {
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://techfundingnews.com",
    "user-agent": "Mozilla/5.0",
    "x-requested-with": "XMLHttpRequest",
}

ONE_YEAR_AGO = datetime.utcnow() - timedelta(days=365)

# UNIQUE: Multiple categories with IDs
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

class TechFundingNews(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/tech_funding"
        )
        self.grid_details = []

    # UNIQUE: Custom date parser
    def parse_date(self, article):
        date_div = article.find("div", class_="cs-meta-date")
        if not date_div:
            return None
        try:
            return datetime.strptime(date_div.get_text(strip=True), "%B %d, %Y")
        except Exception:
            return None

    # UNIQUE: Custom request method
    def get_request_custom(self, url):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return True, r
        except Exception as e:
            self.logger.error(f"Error fetching URL {url}: {e}")
            return False, None

    # UNIQUE: AJAX page fetch with custom payload
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
                self.logger.warning(f"Attempt {attempt + 1} failed for {category_name} page {page}: {e}")
                time.sleep(2)

        return None

    # UNIQUE: Grid parser with date filtering
    def scrape_grid_html(self, html, category_name):
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.find_all("article"):
            try:
                published = self.parse_date(article)
                if not published:
                    continue

                # UNIQUE: Stop when older than 1 year
                if published < ONE_YEAR_AGO:
                    return True

                title_tag = article.find("h2").find("a")
                img = article.find("img")

                categories = article.find("div", class_="cs-meta-category")
                category_text = ", ".join([i.text for i in categories.find_all("li")]) if categories else category_name

                article_data = {
                    "title": title_tag.get_text(strip=True),
                    "url": title_tag["href"],
                    "time": published,
                    "image": img.get("data-pk-src") if img else "",
                    "category": category_text
                }

                # Check if exists (with skip tracking)
                if not self.check_article_exists(article_data["url"]):
                    self.grid_details.append(article_data)

            except Exception:
                continue

        return False

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        data = BeautifulSoup(response.text, "html.parser")
        
        author_meta = data.find("meta", {"name": "author"})
        content_div = data.find("div", class_="entry-content")
        
        return {
            "author": author_meta.get("content", "") if author_meta else "",
            "description": {
                "details": content_div.get_text(strip=True) if content_div else ""
            }
        }

    def save_to_db(self):
        """Save collected articles to database"""
        for grid in self.grid_details:
            try:
                done, response = get_request(grid["url"])
                if not done:
                    continue

                details = self.separate_blog_details(response)
                merged = {**grid, **details}
                merged['created_at'] = datetime.now(ist)

                # Use save_article from BaseScraper
                if self.save_article(merged):
                    self.logger.info(f"✅ Saved: {grid['url']}")

                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error saving article {grid['url']}: {e}")

    def run(self):
        """Main execution logic - UNIQUE: AJAX-based category scraping"""
        self.logger.info("🚀 Starting Tech Funding News scraper")
        
        for cat_name, cfg in CATEGORIES.items():
            page = 1
            self.logger.info(f"📂 Scraping category: {cat_name}")

            while True:
                html = self.fetch_page(cat_name, cfg["cat_id"], page)
                if not html or not html.strip():
                    break

                stop = self.scrape_grid_html(html, cat_name)
                if stop:
                    self.logger.info(f"Reached 1-year-old articles for {cat_name}, stopping")
                    break

                page += 1
                time.sleep(1)

        self.save_to_db()
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ Tech Funding News scraper completed")

def main():
    TechFundingNews().run()
    
if __name__ == "__main__":
    main()