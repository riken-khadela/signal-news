import threading
import time
import traceback
import logging
from tech_funding_news import TechFundingNews
from tech_crunch import TechCrunch
from your_story import YourStory
from inc42 import Inc42

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s - %(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler("log/main.log", mode="a"),
        logging.StreamHandler()
    ]
)

def news_scrapper():
    TechFundingNews().run()
    TechCrunch().run()
    YourStory().run()
    Inc42().run()   

if __name__ == "__main__":
    logging.info("[START] Script initialized...")
    news_scrapper()
    logging.info("[END] Script completed...")