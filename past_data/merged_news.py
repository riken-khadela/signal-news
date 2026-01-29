from datetime import datetime
import pytz
from pymongo import MongoClient, UpdateOne, InsertOne
from datetime import datetime
from dateutil import parser
from logger import CustomLogger

logger = CustomLogger('/home/riken/news-scrapper/news-scrapper/past_data/Logs/Merge')
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

MONGO_URI = "mongodb://admin9:i38kjmx35@localhost:27017/?authSource=admin&authMechanism=SCRAM-SHA-256&readPreference=primary&tls=true&tlsAllowInvalidCertificates=true&directConnection=true"
masterclient = MongoClient(MONGO_URI)
clientdb = masterclient.NEWSSCRAPERDATA
merged_collection = clientdb.MERGED_NEWS

collections_list = [
    "intelligence360",
    "THE_WIRED",
    "ZDNET",
    "BETA_KIT",
    "BUSINESSINSIDER",
    "NEXT_WEB",
    "TECH_EU",
    "TEST_NEXT_WEB",
    "CANARY",
    "CLEANENERGY_WIRE",
    "ADVANCE_MATERIALS_MAGAZINE",
    "THE_QUANTUM_INSIDER",
    "TECH_EU",
    "CNET",
    "MINING",
    "NANOWERK",
    "AZONANO",
    "RIGZONE",
    "PHOCUSWIRE",
    "TECHINASIA",
    "CLEANTECHCHINA",
    "HTN_CO_UK",
    "HEALTHTECHASIA",
    "WORLDOIL",
    "RENEWABLEENERGYWORLD",
    "MobileHealthNews",
    "HEALTHTECHMAGAZINE",
    "FORTUNE",
    "COMPLIANCEWEEK",
    "CRUNCHBASE",
    "SACRA",
    "HEALTHCAREASIAMAGAZINE"
]
    

start_date = datetime(2025, 1, 1, tzinfo=pytz.UTC)
end_date = datetime.utcnow().replace(tzinfo=pytz.UTC)

BATCH_SIZE = 1000  # Tune based on your document size


def parse_datetime_safe(date_str):
    """
    Parses almost any human / ISO datetime string into timezone-aware UTC datetime
    """
    if not date_str:
        return None

    try:
        dt = parser.parse(date_str, fuzzy=True)
    except Exception:
        return None

    if dt.tzinfo:
        dt = dt.astimezone(pytz.UTC)
    else:
        dt = dt.replace(tzinfo=pytz.UTC)

    return dt

def is_date_within_year_range(date_str, year):
    """
    Checks if date is between Jan 1st of `year` and today
    """
    if type(date_str) == str :
        parsed_date = parse_datetime_safe(date_str)
        if not parsed_date:
            return False
    elif type(date_str) == datetime :
        parsed_date = date_str.astimezone(pytz.UTC)

    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    start_date = datetime(year, 1, 1, tzinfo=pytz.UTC)
    within_year = start_date <= parsed_date <= now
    return within_year

for collection_name in collections_list:
    logger.info(f"Processing: {collection_name}")
    
    source_collection = clientdb[collection_name]
    cursor = source_collection.find({}).batch_size(BATCH_SIZE)
    
    bulk_operations = []
    merged_count = 0
    
    data_list = []
    for data in cursor:
        data_copy = data.copy()
        data_copy['source_collection'] = collection_name
        del data_copy['_id']
        
        details = data_copy.get('description',{}).get('details','')
        if not details : continue
        
        time = data_copy.get('time','')
        data_copy['updated_at'] = ist_time
        if time :
            if not is_date_within_year_range(time, year=2025): 
                continue
        
        unique_filter = {
            'source_collection': collection_name,
            'url': str(data['url'])
        }
        data_list.append(data_copy)
        
    urls = [ i['url'] for i in data_list]
    existing_urls = merged_collection.find(
            {"url": {"$in": urls}},
            {"_id": 0, "url": 1}
        )
    existing_url_set = {doc["url"] for doc in existing_urls}
    new_urls = [url for url in urls if url not in existing_url_set]
    for data in data_list :
        if data['url'] in new_urls :
            bulk_operations.append(InsertOne(data))
    merged_collection.bulk_write(bulk_operations, ordered=False)
    merged_count += len(bulk_operations)
    
    logger.info(f"{collection_name}: {merged_count} documents merged")

logger.info(f"Total documents in merged collection: {merged_collection.count_documents({})}")