from email.mime import image
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, intelligence360_client as news_details_client, parse_datetime_safe
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")

URL = "https://www.intelligence360.news/page/"

class Inteligence360(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/intelligence360"
        )
        self.grid_details = []

    def get_grid_details(self):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(URL + str(self.page_index))
            if not done:
                self.logger.error(f"Request failed: {URL}")
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

    def scrape_grid_data(self, html_content):
        """Extract article data from Intelligence360 search results"""
        data = BeautifulSoup(html_content, 'html.parser')
        articles = data.find_all('article')

        extracted_data = []
        for article in articles:
            try:
                article_data = {}
                
                # title and URL
                article_heading = article.find('h2')
                title = article_heading.get_text(strip=True) if article_heading else 'No title'
                article_url = article_heading.find('a').get('href', '') if article_heading else ''
                
                if not article_url:
                    continue
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(article_url):
                    continue
                
                # time
                time_tag = article.find('time')
                date = parse_datetime_safe(time_tag.get('datetime', '') if time_tag else 'No date')
                
                # # Check if too old
                # if date and date != 'No date':
                #     article_time = datetime.fromisoformat(date.replace('Z', '+00:00'))
                #     if self.is_article_too_old(article_time, cutoff_year=2025):
                #         break
                
                # image
                image_tag = article.find('img')
                image_url = image_tag.get('src', '') if image_tag else 'No image'
                
                # author
                author_span = article.find('span', {'class': 'author'})
                author = author_span.get_text(strip=True) if author_span else 'No author'
                
                article_data = {
                    'title': title,
                    'url': article_url,
                    'time': date,
                    'image': image_url,
                    'author': author
                }
                extracted_data.append(article_data)
                
            except Exception as e:
                self.logger.error(f"Error extracting data from article: {e}")
                continue
        
        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            
            # author
            author_meta = data.find('meta', {'name': 'author'})
            if author_meta:
                details['author'] = author_meta.get('content', '')

            # description
            entry_content = data.find_all('div', {'class': 'entry-content'})
            if entry_content:
                details['description']['summary'] = ""
                details['description']['details'] = '  \n'.join([
                    p.get_text(strip=True) for p in entry_content[0].find_all('p')
                ])

        except Exception as e:
            self.logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
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
        """Main execution logic"""
        self.logger.info("🚀 Starting Intelligence360 scraper")
        
        self.page_index = 0
        
        while self.should_continue_scraping():
            self.page_index += 1
            self.logger.info(f"📄 Processing page {self.page_index}")
            
            self.grid_details = []
            self.get_grid_details()
            
            if self.grid_details:
                self.check_db_grid()
            else:
                self.logger.warning("No articles found, stopping")
                break
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ Intelligence360 scraper completed")

def main():
    Inteligence360().run()
    
if __name__ == "__main__":
    main()
