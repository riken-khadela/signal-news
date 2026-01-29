import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, news_details_client
from base_scraper import BaseScraper
from logger import CustomLogger
import pytz

ist = pytz.timezone("Asia/Kolkata")
URL = "https://techcrunch.com/latest/page/"

class TechCrunch(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/tech_crunch"
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
        """Extract article data from TechCrunch search results"""
        data = BeautifulSoup(html_content, 'html.parser')
        
        articles = [i for i in data.find_all('li', {'class': 'post'}) if i.find('img')]
        
        extracted_data = []
        for article in articles:
            try:
                # Extract title from the span inside the title link
                title_span = article.find('h3')
                if not title_span:
                    continue
                    
                article_url = title_span.find('a').get('href', '')
                title = title_span.get_text(strip=True)
                
                if title == 'No title':
                    continue

                # Check if exists (with skip tracking)
                if self.check_article_exists(article_url):
                    continue

                # Extract date
                date_span = article.find('time')
                date = date_span.get('datetime', '') if date_span else 'No date'
                
                # # Check if too old
                # if date and date != 'No date':
                #     article_time = datetime.fromisoformat(date.replace('Z', '+00:00'))
                #     if self.is_article_too_old(article_time, cutoff_year=2025):
                #         break  # Stop processing this page
                
                # Extract image URL
                img_tag = article.find('img')
                image_url = img_tag.get('src', '') if img_tag else 'No image'
                
                # Extract category (News, etc.)
                category_span = article.find('div', class_='loop-card__cat-group')
                category = category_span.get_text(strip=True) if category_span else 'No category'
                
                # Store the extracted data
                article_data = {
                    'title': title,
                    'url': article_url,
                    'time': parse_datetime_safe(date),
                    'image': image_url,
                    'category': category
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
            summary_elem = data.find('p', {'id': 'speakable-summary'})
            if summary_elem:
                details['description']['summary'] = summary_elem.get_text(strip=True)
            
            content_elem = data.find('div', {'class': 'wp-block-post-content'})
            if content_elem:
                full_text = content_elem.get_text(strip=True)
                summary_text = details['description'].get('summary', '')
                details['description']['details'] = full_text.replace(summary_text, '')

        except Exception as e:
            self.logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
            try:
                # Skip if already exists (handled by check_article_exists in scrape_grid_data)
                
                done, response = get_request(grid["url"])
                if not done:
                    self.logger.warning(f"Failed fetching: {grid['url']}")
                    continue

                details = self.separate_blog_details(response)
                merged = {**details, **grid}
                
                # Convert time if it's a string
                if isinstance(merged["time"], str) and merged["time"]:
                    try:
                        merged["time"] = datetime.strptime(
                            merged["time"], "%B %d, %Y"
                        )
                    except Exception:
                        merged["time"] = datetime.utcnow()
                
                merged['created_at'] = datetime.now(ist)

                # Use save_article from BaseScraper
                if self.save_article(merged):
                    self.logger.info(f"✅ Saved: {merged['url']}")

                time.sleep(1) 
            except Exception as e:
                self.logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        """Main execution logic"""
        self.logger.info("🚀 Starting TechCrunch scraper")
        
        while self.should_continue_scraping():
            self.logger.info(f"📄 Processing page {self.page_index}")
            
            self.grid_details = []
            self.get_grid_details()
            
            if self.grid_details:
                self.check_db_grid()
            else:
                self.logger.warning("No articles found, stopping")
                break
            
            self.page_index += 1
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ TechCrunch scraper completed")

def main():
    TechCrunch().run()
    
if __name__ == "__main__":
    main()
