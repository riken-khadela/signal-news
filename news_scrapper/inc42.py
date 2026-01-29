import logging
import time
from datetime import datetime

from bs4 import BeautifulSoup
from requests import RequestException
from news_scrapper.settings import get_request, news_details_client, save_run_stats
from logger import CustomLogger
logger = CustomLogger(log_folder="/home/riken/news-scrapper/news-scrapper/log/Inc42")

URL = "https://inc42.com/buzz/?utm_medium=referral&utm_source=menu"


class Inc42:
    def __init__(self):
        self.grid_details = []
        self.inserted_count = 0
        # Ensure MongoDB has an index on URL for speed
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0

    def get_grid_details(self):
        """Scrape the grid (listing) page."""
        try:
            done, response = get_request(URL)
            if not done:
                logger.error(f"Request failed: {URL}")
                return []

            data = BeautifulSoup(response.text, "html.parser")
            main_div = data.find("div", {"id": "primary"})
            if not main_div:
                logger.warning("No main div found on page.")
                return []

            for content_div in main_div.find_all("div", {"class": "card-wrapper"}):
                tmp = {
                    "title": "",
                    "url": "",
                    "author": "",
                    "image": "",
                    "time": "",
                    "category" : ""
                }

                # category
                category = content_div.find('span',{'class':'post-category'})
                if category :
                    tmp['category'] = category.text
                
                # title + url
                title_div = content_div.find("h2")
                if title_div:
                    tmp["title"] = title_div.get_text(strip=True)
                    anchor_tag = title_div.find("a")
                    tmp["url"] = anchor_tag.get("href") if anchor_tag else ""

                # publish date
                date_span = content_div.find("span", {"class": "date"})
                tmp["time"] = date_span.get_text(strip=True) if date_span else ""

                # author
                author_span = content_div.find("span", {"class": "author"})
                tmp["author"] = author_span.get_text(strip=True) if author_span else ""

                # image
                img_div = content_div.find("img")
                if img_div:
                    tmp["image"] = img_div.get("data-cfsrc") or img_div.get("src")

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

    def seprate_blog_details(self, response):
        """Parse the full blog page for details."""
        details = {"description": {}}
        try:
            data = BeautifulSoup(response.text, "html.parser")

            # summary
            summery_div = data.find('div',{'class':'single-post-summary'})
            if summery_div :
                details['description']['summery'] = summery_div.text.strip().replace('SUMMARY\n','').split('\n')
            
            # details
            details_div = data.find("div", {"class": "single-post-content"})
            if details_div:
                details["description"]["details"] = details_div.get_text(
                    separator="\n", strip=True
                )

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
#     Inc42().run()
