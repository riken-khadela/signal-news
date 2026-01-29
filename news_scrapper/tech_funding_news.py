import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from news_scrapper.settings import get_request, get_scrape_do_requests, news_details_client, save_run_stats, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/log/TechFundingNews")

URLS = [
    "https://techfundingnews.com/category/acquisition/",
    "https://techfundingnews.com/category/top-funding-rounds/"
]


class TechFundingNews:
    def __init__(self):
        self.grid_details = []
        self.inserted_count = 0
        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self, url):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(url)
            # done, response = get_scrape_do_requests(url)
            if not done:
                logger.error(f"Request failed: {url}")
                return []

            self.scrape_grid_data(response.text)
            # with open("tech_in_asia_response.html", "w", encoding="utf-8") as f:f.write(response.text)
            
            logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_grid_details: {e}")
            return []

    def scrape_grid_data(self, html_content):
        """
        Extract article data from YourStory search results
        """
        data = BeautifulSoup(html_content, 'html.parser')
        
        articles = data.find('div',{'class':'cs-posts-area__list'}) 

        if not articles:
            logger.warning("No articles found on the page.")
            return []
        
        for article in articles.find_all('article'):
            try:
                article_url = ""
                # Extract title from the span inside the title link
                title_span = article.find('h2')
                if title_span :
                    article_url = title_span.find('a').get('href', '')
                    
                    title = title_span.get_text(strip=True) if title_span else 'No title'
                    if title == 'No title':
                        continue

                # Extract date
                date_span = article.find('div', class_='cs-meta-date')
                date = date_span.get_text(strip=True) if date_span else 'No date'

                # Extract image URL
                img_tag = article.find('img')
                image_url = img_tag.get('data-pk-src', '') if img_tag else 'No image'
                
                # Extract category (News, etc.)
                category_span = article.find('div', class_='cs-meta-category').find_all('li')
                category = [i.text for i in category_span]
                category = ', '.join(category) if category else 'No category'

                # Store the extracted data
                article_data = {
                    'title': title,
                    'url': article_url,
                    'time': datetime.strptime(date, "%B %d, %Y"),
                    'image': image_url,
                    'category': category
                }
                
                self.grid_details.append(article_data)
                
            except Exception as e:
                print(f"Error extracting data from article: {e}")
                continue
        
        return self.grid_details

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            #  author
            details['author'] = data.find('meta',{'name':'author'}).get('content','')

            # description
            details['description']['summary'] = []
            details['description']['details'] = data.find('div',{'class':'entry-content'}).get_text(strip=True)
        except Exception as e:
            logger.error(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
            try:
                if news_details_client.find_one({"url": grid["url"]}):
                    logger.info(f"Skipping (already in DB): {grid['url']}")
                    continue

                done, response = get_request(grid["url"])
                if not done:
                    logger.warning(f"Failed fetching: {grid['url']}")
                    continue
                
                details = self.separate_blog_details(response)
                merged = {**details, **grid}
                # Convert time if it's a string
                if isinstance(merged["time"], str) and merged["time"]:
                    try:
                        # TODO: adjust strptime format as per site’s time format
                        merged["time"] = datetime.strptime(
                            merged["time"], "%B %d, %Y"
                        )
                    except Exception:
                        merged["time"] = datetime.utcnow()

                news_details_client.update_one(
                    {"url": merged["url"]},
                    {"$set": {
                        "title": merged["title"],
                        "author": merged["author"],
                        "image": merged["image"],
                        "description": merged["description"],
                        "time": merged["time"],
                        "category" : merged["category"]
                    }},
                    upsert=True
                )
                self.inserted_count += 1
                logger.info(f"Inserted new article: {merged['url']}")

                time.sleep(1) 
            except Exception as e:
                logger.error(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        for url in URLS:
            self.get_grid_details(url)
        if self.grid_details:
            self.check_db_grid()
        save_run_stats(self.inserted_count)

# if __name__ == "__main__":
#     TechFundingNews().run()
