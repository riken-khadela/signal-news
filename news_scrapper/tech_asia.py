import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, news_details_client, yourstory_scrape_do_requests
from datetime import datetime

URL = "https://www.techinasia.com/news/byd-overtakes-tesla-europes-july-car-sales"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s - %(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler("log/main.log", mode="a"),
        logging.StreamHandler()
    ]
)


class TechCrunch:
    def __init__(self):
        self.grid_details = []

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0
        self.skipped_urls = 0

    def get_grid_details(self):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(URL)
            # done, response = get_scrape_do_requests(URL)
            if not done:
                logging.error(f"Request failed: {URL}")
                return []

            self.grid_details = self.scrape_grid_data(response.text)
            # with open("tech_in_asia_response.html", "w", encoding="utf-8") as f:f.write(response.text)
            
            logging.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            logging.exception(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            logging.exception(f"Unexpected error in get_grid_details: {e}")
            return []

    def scrape_grid_data(self, html_content):
        """
        Extract article data from YourStory search results
        """
        data = BeautifulSoup(html_content, 'html.parser')
        
        articles = data.find('div',{'class':'cs-posts-area__list'}) 

        if not articles:
            logging.warning("No articles found on the page.")
            return []
        
        extracted_data = []
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
                    'date': date,
                    'image_url': image_url,
                    'category': category
                }
                
                extracted_data.append(article_data)
                
            except Exception as e:
                print(f"Error extracting data from article: {e}")
                continue
        
        return extracted_data

    def separate_blog_details(self, response):
        """Parse the full blog page for details."""
        with open("tech_in_asia_response.html", "w", encoding="utf-8") as f:f.write(response.text)
        details = {"description": {}}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            #  author
            details['author'] = data.find('meta',{'name':'author'}).get('content','')

            # description
            details['description']['summary'] = data.find('p',{'id':'speakable-summary'}).get_text(strip=True)
            details['description']['details'] = data.find('div',{'class':'wp-block-post-content'}).get_text(strip=True).replace(details['description']['summary'],'')
            breakpoint()
        except Exception as e:
            logging.exception(f"Error parsing blog details: {e}")

        return details

    def check_db_grid(self):
        """Check DB before fetching details; skip if exists."""
        for grid in self.grid_details:
            try:
                if news_details_client.find_one({"url": grid["url"]}):
                    logging.info(f"Skipping (already in DB): {grid['url']}")
                    continue

                done, response = get_request(grid["url"])
                if not done:
                    logging.warning(f"Failed fetching: {grid['url']}")
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
                logging.info(f"Inserted new article: {merged['url']}")

                time.sleep(1) 
            except Exception as e:
                logging.exception(f"Error in check_db_grid for {grid['url']}: {e}")

    def run(self):
        self.get_grid_details()
        if self.grid_details:
            self.check_db_grid()


if __name__ == "__main__":
    TechCrunch().run()
