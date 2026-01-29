import random, pymongo, logging, re, time, json
from pymongo import MongoClient, UpdateOne, InsertOne
from pymongo.errors import BulkWriteError
import settings as cf 
from bot import get_google_search_results, parse_google_results

CONFIG_FILE = "/home/riken/news-scrapper/news-scrapper/config.json"
with open(CONFIG_FILE, "r") as f: config = json.load(f)
mongo_db_connection = config["mongo_db_connection"]

logger = cf.logger(f'link scrapper main.log')
masterclient = MongoClient(mongo_db_connection)
news_scrapper = masterclient.NEWSSCRAPER
sector_collection = news_scrapper.keywords

news_scrapper_data = masterclient.NEWSSCRAPERDATA
news_url_1 = news_scrapper_data.news_url_1
news_details_1 = news_scrapper_data.news_details_1

KEYWORDS = [
    "Funding & Investment",
    "Product & Technology Innovation",
    "Acquistions"
]

LOCATION = ["US"]

def format_field(value):
    values = value.split("|")
    result = {}
    non_blank_index = 1  

    for val in values:
        val = val.strip()
        if val:  
            result[str(non_blank_index)] = val
            non_blank_index += 1

    return result

def insert_multiple_urls_from_google(documents_list):
    news_url_1.create_index([("url", 1)], unique=True)
    bulk_operations = []
    update_details=[]
    
    
    for documents in documents_list:
        for obj in documents:
            try:
                existing_doc = news_url_1.find_one({"url": obj["url"]})
                if not existing_doc:
                    bulk_operations.append(pymongo.InsertOne(obj))
                    
                if existing_doc:
                    logger.info("===[ Duplicate Found ]===")
                    Sector = existing_doc.get('sector')
                    Tag = existing_doc.get('tag')
                    
                    if obj['sector'] and str(obj['sector']).strip() not in  str(existing_doc.get('sector')).strip():
                        Sector = str(existing_doc.get('sector'))+'|'+str(obj['sector'])
                        
                    if obj['tag'] and str(obj['tag']).lower().strip() not in  str(existing_doc.get('tag')).lower().strip():
                        Tag = str(existing_doc.get('tag'))+'|'+str(obj['tag'])
                    
                    COUNT =existing_doc.get('count') + 1
                    update_query = {
                        "$set": {
                            'count': COUNT, 
                            'sector' : Sector,
                            'tag' : Tag,
                        },
                    }
                    bulk_operations.append(UpdateOne({"_id": existing_doc["_id"]}, update_query))
                    
                    url=obj["url"]
                    regex_pattern = f'^{re.escape(obj["url"])}$'
                    doc = news_details_1.find_one({"url": {"$regex": regex_pattern, "$options": 'i'}})
                    if doc:
                        append_fields = {
                            "search_sector": format_field(Sector),
                            "search_tag": format_field(Tag),
                            "count": COUNT
                        }

                        update_details.append(UpdateOne({"_id": doc["_id"]}, {"$set": append_fields}))
            except Exception as e:
                logger.error("Error processing document: %s", str(e))
    
    try:
        if bulk_operations:
            result = news_url_1.bulk_write(bulk_operations)
            logger.info("===>>  Total Inserted Records: %d", result.inserted_count)
       
        if update_details:
            result = news_details_1.bulk_write(update_details)
            logger.info("===>>  Total Updated Records: %d", result.modified_count)

    except BulkWriteError as e:
        logger.error("Bulk write error: %s", e.details)

def get_sector_data():
    return sector_collection.find()


def collect_page_details(sector, keywords, site_name, geo_locations = ['US']):
    logger = cf.logger(f'{site_name.split(".")[0]}.log')
    data = []
    for geo in geo_locations:
        search_term = f"{sector['sector']} + {keywords}"
        html = get_google_search_results(search_term, site_name, 'm', logger)
        if html:
            data = parse_google_results(html, sector, keywords, search_term, site_name, logger)
            time.sleep(2)
        else:
            logger.warning("No HTML returned for: %s", search_term)

    return data

def main():
    all_urls = []
    for keyword in KEYWORDS :
        for sector in get_sector_data() :
            
            print('searching for :',sector['sector'], '+', keyword)
            tech_crunch_ = collect_page_details(sector, keyword, "techcrunch.com", LOCATION)
            if tech_crunch_ :
                all_urls.append(tech_crunch_)
                
            the_verge_ = collect_page_details(sector, keyword, "theverge.com", LOCATION)
            if the_verge_ :
                all_urls.append(the_verge_)

            digital_trends_ = collect_page_details(sector, keyword, "digitaltrends.com", LOCATION)
            if digital_trends_ :
                all_urls.append(digital_trends_)

            inc42_ = collect_page_details(sector, keyword, "inc42.com", LOCATION)
            if inc42_ :
                all_urls.append(inc42_)

            your_story_ = collect_page_details(sector, keyword, "yourstory.com", LOCATION)
            if your_story_ :
                all_urls.append(your_story_)
            
            crunchbase_ = collect_page_details(sector, keyword, "news.crunchbase.com", LOCATION)
            if crunchbase_ :
                all_urls.append(crunchbase_)
            
            
            if all_urls :
                for _ in range(3):
                    try:
                        insert_multiple_urls_from_google(all_urls)
                    except Exception as e:
                        logger.error("Error inserting URLs: %s", str(e))
                        time.sleep(5)
                all_urls = []
        