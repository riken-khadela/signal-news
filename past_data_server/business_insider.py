from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from urllib.parse import urljoin
from settings import get_request, BUSINESSINSIDER_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URLS_list = [
    'https://www.businessinsider.com/strategy'
]
BASE_URL = "https://www.businessinsider.com"
# UNIQUE: Business Insider uses API for pagination
API_BASE_URL = "https://www.businessinsider.com/ajax/content-api/vertical?templateId=legacy-river&capiVer=2&riverSize=50&riverNextPageToken="

class BusinessInsider(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/businessinsider"
        )
        self.grid_details = []
        self.next_url = ""  # UNIQUE: For API pagination

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(url)
            if not done:
                self.logger.error(f"Request failed: {url}")
                return []

            self.grid_details = self.scrape_grid_data(response.text)
            self.logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            self.logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in get_grid_details: {e}")
            return []

    def extract_best_image(self, img_tag):
        """UNIQUE: Extract best quality image from data-srcs"""
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

    def parse_articles(self, rendered_html, category):
        """UNIQUE: Parse articles from rendered HTML"""
        soup = BeautifulSoup(rendered_html, "lxml")
        articles = []

        for node in soup.select("article[data-component-type='tout']"):
            title_el = node.select_one("h3.tout-title a")
            img_el = node.select_one("img.lazy-image")
            summary_el = node.select_one(".tout-copy")
            read_time_el = node.select_one(".tout-read-time")

            if not title_el:
                continue
            
            url = urljoin(BASE_URL, title_el.get("href"))
            
            # Check if exists (with skip tracking)
            if self.check_article_exists(url):
                continue

            articles.append({
                "category": category,
                "title": title_el.get_text(strip=True),
                "url": url,
                "image": self.extract_best_image(img_el),
                "summary": summary_el.get_text(strip=True) if summary_el else None,
                "read_time": read_time_el.get_text(strip=True) if read_time_el else None,
            })

        return articles

    def scrape_grid_data(self, html_content):
        """UNIQUE: Business Insider uses API-based pagination"""
        data = BeautifulSoup(html_content, 'html.parser')
        extracted_data = []
        
        category = "strategy"
        
        # Get initial next URL from page
        sub_vertical_divs = data.find_all('div', {'class': 'sub-vertical'})
        if sub_vertical_divs:
            next_token = sub_vertical_divs[-1].get('data-next', '').split('Token=')[-1]
            self.next_url = f"{API_BASE_URL}{next_token}&id={category}"
        
        # Parse initial articles
        articles_list = self.parse_articles(html_content, category)
        extracted_data.extend(articles_list)
        
        # UNIQUE: Process articles inline (save as we go)
        self.check_db_grid(articles_list)
        
        # UNIQUE: Continue with API pagination
        while self.should_continue_scraping():
            try:
                done, response = get_request(self.next_url)
                if not done:
                    break
                
                payload = response.json()
                block = payload.get(category, {})
                rendered_html = block.get("rendered")
                
                if not rendered_html:
                    break
                
                articles_list = self.parse_articles(rendered_html, category)
                
                # UNIQUE: Process inline
                self.check_db_grid(articles_list)
                extracted_data.extend(articles_list)
                
                # Check for next page
                if payload.get(category, {}).get('links', {}) == {}:
                    break
                
                next_link = payload[category]['links'].get('next', '')
                if not next_link:
                    break
                
                next_token = next_link.split('Token=')[-1]
                self.next_url = f"{API_BASE_URL}{next_token}&id={category}"
                
            except Exception as e:
                self.logger.error(f"Error in API pagination: {e}")
                break
        
        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}, "time": '', "author": ""}
        try:
            
            data = BeautifulSoup(response.text, "html.parser")
            
            # author
            author = data.find("a", {"class": "byline-author-name"})
            details['author'] = author.get_text(strip=True) if author else ""

            # time
            time_ele = data.find('time')
            if time_ele:
                details['time'] = parse_datetime_safe(time_ele.get('data-timestamp'))

            # summary
            summary_ele = data.find('div', {'class': 'post-summary-bullets'})
            if summary_ele:
                details['description']['summary'] = ' \n'.join([
                    i.get_text(strip=True) for i in summary_ele.find_all('li')
                ])
            
            # UNIQUE: Extract specific tags from post body
            ALLOWED_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6"]
            details_ele = data.find('section', {'class': 'post-story-body-content'})
            if details_ele:
                texts = []
                for tag in details_ele.find_all(ALLOWED_TAGS, recursive=True):
                    text = tag.get_text(" ", strip=True)
                    if text:
                        texts.append(text)
                
                details['description']['details'] = ' \n'.join(texts)
                
        except Exception as e:
            self.logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self, articles_list=[]):
        """Check DB before fetching details; skip if exists."""
        if not articles_list:
            articles_list = self.grid_details
        
        for grid in articles_list:
            try:
                done, response = get_request(f"{grid['url']}")
                if not done:
                    self.logger.warning(f"Failed fetching: {grid['url']}")
                    continue
                
                details = self.separate_blog_details(response)
                if details == False:
                    continue
                
                merged = {**details, **grid}
                merged['created_at'] = datetime.now(ist)

                # Use save_article from BaseScraper
                if self.save_article(merged):
                    self.logger.info(f"✅ Saved: {merged['url']}")

                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        """Main execution logic - UNIQUE: Uses API pagination"""
        self.logger.info("🚀 Starting Business Insider scraper")
        
        for url in URLS_list:
            self.logger.info(f"📂 Processing: {url}")
            self.page_index = 0
            self.consecutive_skips = 0
            
            # UNIQUE: Business Insider processes everything in scrape_grid_data
            # due to API pagination, so we only call it once
            self.grid_details = []
            self.get_grid_details(url)
            
            # Articles are already processed inline
            break  # Only process once since API handles pagination
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ Business Insider scraper completed")

def main():
    BusinessInsider().run()
    
if __name__ == "__main__":
    main()
