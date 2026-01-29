import logging
import random
import time, re
from datetime import datetime

from bs4 import BeautifulSoup
from requests import RequestException
from news_scrapper.settings import get_request, news_details_client
from logger import CustomLogger
from datetime import datetime

logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/log/vc_circle")

URL = "https://www.vccircle.com/search/result/tech/all/"
BASE_URL = "https://www.vccircle.com"

class VcCircle:
    def __init__(self):
        self.grid_details = []

        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0
        self.page_index = 0

    
    
    def get_grid_details(self):
        """Scrape the grid (listing) page."""
        self.page_index += 1
        try:
            done, response = get_request(f"{URL}{self.page_index}")
            if not done:
                logger.error(f"Request failed: {URL}")
                return []
            with open("/home/riken/news-scrapper/news-scrapper/vccircle.html",'w') as f: f.write(response.text)
            data = BeautifulSoup(response.text, "html.parser")
            main_div = data.find_all("div",class_=re.compile(r"searchListing_article-list__"))
            if not main_div:
                logger.warning("No main div found on page.")
                return []

            for content_div in main_div:
                tmp = {
                    "title": "",
                    "url": "",
                    "author": "",
                    "image": "",
                    "time": "",
                    "category" : ""
                }

                # category
                tmp['category'] = "Tech"
                
                # title + url
                title_div = content_div.find("h4")
                if title_div:
                    tmp["title"] = title_div.get_text(strip=True)
                
                anchor_tag = content_div.find("a")
                if anchor_tag:
                    tmp['url'] = BASE_URL
                    tmp["url"] += anchor_tag.get("href") if anchor_tag else ""

                # publish date
                date_span = content_div.find("div",class_=re.compile(r"newsCard_date__"))
                tmp["time"] = f"{date_span.text},{datetime.now().year}" if date_span else ""

                # author
                author_span = content_div.find("li")
                tmp["author"] = author_span.get_text(strip=True) if author_span else ""

                # image
                img_div = content_div.find("img")
                if img_div:
                    img_src = img_div.get("data-cfsrc") or img_div.get("src")
                    tmp['image'] = img_src if img_src.startswith("http") else BASE_URL + img_src

                # accept only if all required fields are filled
                if all(str(v).strip() for v in tmp.values()):
                    self.grid_details.append(tmp)
                else:
                    logger.warning(f"This url has been skipped : {tmp['url']}")
                    logger.info(f"tmp dict : {tmp}")

            logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except RequestException as e:
            logger.error(f"Request error while fetching grid: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_grid_details: {e}")
            return []
    
    def seprate_description(self, article):
        paragraphs = []
        for p in article.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)

        final_text = "\n\n".join(paragraphs)
        return final_text
    
    def seprate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}}
        try:
            data = BeautifulSoup(response.text, "html.parser")
            # summary
            details_div = data.find("div",class_=re.compile(r"articleDetail_article-content__"))
            if details_div :
                details['description']['details'] = self.seprate_description(details_div)
            
            details["description"]["summery"] = ""

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
                
                # premiumArticle_premium-member__Ng9ho
                data = BeautifulSoup(response.text, "html.parser")
                main_div = data.find("a",class_=re.compile(r"premiumArticle_premium-member__"))
                if main_div:
                    if main_div.text == "Become a Premium member":
                        logger.warning(f"Failed fetching for Premium blogs: {grid['url']}")
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
                logger.info(f"Inserted new article: {merged['url']}")

                time.sleep(1) 
            except Exception as e:
                logger.error(f"Error in check_db_grid for {grid['url']}: {e}")
    
    def run(self):
        
        while True :
            self.grid_details = []
            
            grid_details = self.get_grid_details()
            if not grid_details:
                break
            
            if self.grid_details:
                self.check_db_grid()

            time.sleep(random.randint(5,7))

if __name__ == "__main__":
    VcCircle().run()
