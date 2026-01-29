import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from news_scrapper.settings import get_request, get_scrape_do_requests, news_details_client, save_run_stats, yourstory_scrape_do_requests
from datetime import datetime
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/log/YourStory")

URL = "https://yourstory.com/search?page=1&tag=Just%20In"

class YourStory:
    def __init__(self):
        self.grid_details = []
        self.inserted_count = 0
        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self):
        """Scrape the grid (listing) page."""
        try:
            done, response = yourstory_scrape_do_requests(URL)
            if not done:
                logger.error(f"Request failed: {URL}")
                return []

            data = BeautifulSoup(response.text, "html.parser")

            self.grid_details = self.scrape_yourstory_data(response.text)
            # with open("yourstory_response.html", "w", encoding="utf-8") as f:f.write(response.text)
            
            logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_grid_details: {e}")
            return []

    def scrape_yourstory_data(self, html_content):
        """
        Extract article data from YourStory search results
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all article li elements
        articles = soup.find_all('li', class_='sc-c9f6afaa-0 cuRydj')
        
        extracted_data = []
        
        for article in articles:
            try:
                # Extract article URL and title
                title_link = article.find('a', class_='sc-43a0d796-0 khwyEN')
                if not title_link:
                    continue
                    
                article_url = 'https://yourstory.com' + title_link.get('href', '')
                
                # Extract title from the span inside the title link
                title_span = article.find('span', attrs={'pathname': '/search'})
                title = title_span.get_text(strip=True) if title_span else 'No title'

                if title == 'No title':
                    continue

                # Extract date
                date_span = article.find('span', class_='sc-36431a7-0 dpmmXH')
                date = date_span.get_text(strip=True) if date_span else 'No date'
                
                # Extract image URL
                img_tag = article.find('img', class_='sc-c6064b83-0 ddvyxk')
                image_url = img_tag.get('src', '') if img_tag else 'No image'
                
                # Extract category (News, etc.)
                category_span = article.find('span', class_='sc-c9f6afaa-4 exBjWC')
                category = category_span.get_text(strip=True) if category_span else 'No category'
                
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

    def seprate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}}
        try:
            data = BeautifulSoup(response.text, "html.parser")

            data.find('div',{'id':'S:1'})
            json_scripts = data.find_all('script', type='application/ld+json')
            if json_scripts :
                json_data = json.loads(json_scripts[-1].string)
                details['title'] = json_data.get('headline', '')
                if json_data.get('author', []):
                    details['author'] = json_data.get('author', [])[-1].get('name', '')
                details['time'] = json_data.get('datePublished', '')
                details['description']['summery'] = json_data.get('description', '').replace('SUMMARY\n','').split('\n')
                details['image'] = json_data.get('image', '')

            # header
            header_ele = data.find('header',{'id':'article-start-row'})
            header_ele.find('p', class_=lambda x: x and 'font-neue' in x)
            if header_ele :
                # title
                title_elem = header_ele.find('h1')
                if title_elem:
                    details['title'] = title_elem.get_text(strip=True)

                # image
                img_ele = header_ele.find('img',{'class':'object-cover'})
                if img_ele :
                    att_list = img_ele.get_attribute_list('srcset')
                    details['image'] = att_list[-1] if att_list else ''

                # date
                date_elem = header_ele.find('p', class_=lambda x: x and 'font-neue' in x)
                if date_elem:
                    date_timeframe = date_elem.get_text(strip=True).split(' ,')[0]
                    details['time'] = datetime.strptime(date_timeframe, "%A %B %d, %Y")

            # summary
            summery_div = data.find('h2')
            if summery_div :
                details['description']['summery'] = summery_div.text.strip().replace('SUMMARY\n','').split('\n')
            
            # details
            details_div = data.find('div',{'class':'quill-content'})
            if details_div:
                details["description"]["details"] = details_div.get_text(separator="\n", strip=True).split('\nSign up')[0]
                
            # author
            author_anchor = data.find('a',{'class':'article_author_name'})
            if author_anchor:
                details['author'] = author_anchor.get_text(strip=True)

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

                done, response = get_scrape_do_requests(grid["url"])
                if not done:
                    logger.warning(f"Failed fetching: {grid['url']}")
                    continue

                details = self.seprate_blog_details(response)
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
        self.get_grid_details()
        if self.grid_details:
            self.check_db_grid()
        save_run_stats(self.inserted_count)

# if __name__ == "__main__":
#     YourStory().run()
