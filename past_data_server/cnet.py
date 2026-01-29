from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, CNET_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

class Cnet(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/cnet"
        )
        self.grid_details = []
        # UNIQUE: API pagination with limit/offset
        self.limit = 200
        self.offset = 0

    def get_grid_details(self):
        """UNIQUE: Scrape using CNET API with limit/offset pagination"""
        while self.should_continue_scraping():
            try:
                # UNIQUE: Uses API endpoint with limit and offset
                api_url = f"https://bender.prod.cnet.tech/api/neutron/sitemaps/cnet/articles/year/2025/web?limit={self.limit}&offset={self.offset}&apiKey=073ecda0-c8e1-42ea-8d06-60b4ee845981"
                done, response = get_request(api_url)
                
                if not done:
                    self.logger.error(f"Request failed")
                    continue
                
                json_data = response.json()
                articles = self.scrape_grid_data(json_data)
                self.grid_details.append(articles)
                
                self.offset += self.limit
                
                # Check if we've reached the end
                if json_data.get('data', {}) == {}:
                    break
                if json_data.get('data', {}).get('paging', {}).get('total', 0) <= self.offset:
                    break

                self.logger.info(f"Collected {len(self.grid_details)} batches")

            except RequestException as e:
                self.logger.error(f"Request error while fetching grid: {e}")
                return []
            except Exception as e:
                self.logger.error(f"Unexpected error in get_grid_details: {e}")
                return []
        
        return self.grid_details

    def generate_cnet_absolute_url(self, item: dict) -> str:
        """UNIQUE: Generate CNET URL from API data"""
        base = "https://www.cnet.com"

        # Extract hub path and normalize
        hub_path = item.get("metaData", {}).get("hubTopicPathString", "")
        parts = hub_path.split("^")

        # CNET uses the first two levels only
        path_parts = [
            p.lower()
            .replace("&", "and")
            .replace(" ", "-")
            for p in parts[:2]
        ]

        slug = item.get("slug")

        return f"{base}/{'/'.join(path_parts)}/{slug}/"

    def scrape_grid_data(self, json_response):
        """UNIQUE: Extract article data from JSON API response"""
        data = json_response.get('data', {})
        data_dict = []

        for items in data.get('items', []):
            url = self.generate_cnet_absolute_url(items)

            # Check if exists (with skip tracking)
            if self.check_article_exists(url):
                continue
            tmp = {
                'url': url,
                'title': items.get('title', ''),
                'image': items.get('image', {}).get('path', ''),
                'dateCreated': parse_datetime_safe(items.get('dateCreated', '')),
                'dateUpdated': parse_datetime_safe(items.get('dateUpdated', '')),
                'datePublished': parse_datetime_safe(items.get('datePublished', '')),
            }
            data_dict.append(tmp)

        return data_dict

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {
            "author": "",
            "description": {
                "summary": "",
                "details": ""
            }
        }
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # author
            author_ele = data.find('a', {'class': 'c-globalAuthor_link'})
            if author_ele:
                details['author'] = author_ele.get_text(strip=True)

            # description summary
            summery_ele = data.find('p', {'class': 'c-contentHeader_description'})
            if summery_ele:
                details['description']['summary'] = summery_ele.get_text(strip=True)
            
            # description details
            details_ele = data.find('article')
            if details_ele:
                details['description']['details'] = details_ele.get_text()

        except Exception as e:
            self.logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        # UNIQUE: grid_details is a list of lists
        for grid_items in self.grid_details:
            for grid in grid_items:
                try:
                    done, response = get_request(grid["url"])
                    if not done:
                        self.logger.warning(f"Failed fetching: {grid['url']}")
                        continue
                    
                    details = self.separate_blog_details(response)
                    merged = {**details, **grid}
                    merged['created_at'] = datetime.now(ist)

                    # Use save_article from BaseScraper
                    if self.save_article(merged):
                        self.logger.info(f"✅ Saved: {merged['url']}")

                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        """Main execution logic - UNIQUE: API-based scraping"""
        self.logger.info("🚀 Starting CNET scraper")
        
        self.grid_details = []
        self.get_grid_details()
        
        if self.grid_details:
            self.check_db_grid()
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ CNET scraper completed")

def main():
    Cnet().run()
    
if __name__ == "__main__":
    main()
