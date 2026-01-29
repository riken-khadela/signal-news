from datetime import datetime
import pytz
from pymongo import MongoClient, UpdateOne
from datetime import datetime
from dateutil import parser
from logger import CustomLogger

logger = CustomLogger('/home/riken/news-scrapper/news-scrapper/past_data/Logs/Merge')

MONGO_URI = "mongodb://admin9:i38kjmx35@localhost:27017/?authSource=admin&authMechanism=SCRAM-SHA-256&readPreference=primary&tls=true&tlsAllowInvalidCertificates=true&directConnection=true"
masterclient = MongoClient(MONGO_URI)
clientdb = masterclient.NEWSSCRAPERDATA
merged_collection = clientdb.MERGED_NEWS

collections_list = [
    "ADVANCE_MATERIALS_MAGAZINE", 
    "AZONANO", 
    "BETA_KIT",
    "CANARY",
    "CLEANENERGY_WIRE", 
    "CLEANTECHCHINA", 
    "CNET", 
    "COMPLIANCEWEEK",
    "CRUNCHBASE",
    "FORTUNE",
    "HEALTHCAREASIAMAGAZINE", 
    "HEALTHTECHASIA", 
    "HEALTHTECHMAGAZINE", 
    "HTN_CO_UK", 
    "MINING", 
    "MobileHealthNews"
    "NANOWERK", 
    "TEST_NEXT_WEB",
    "RENEWABLEENERGYWORLD",
    "RIGZONE",
    "SACRA",
    "TECHINASIA",
    "TECH_EU", 
    "TECH_IN_ASIA",
    "THE_QUANTUM_INSIDER", 
    "THE_WIRED", 
    "WORLDOIL",
    "ZDNET",
    "businessinsider", 
    "intelligence360",
]

start_date = datetime(2025, 1, 1, tzinfo=pytz.UTC)
end_date = datetime.utcnow().replace(tzinfo=pytz.UTC)

BATCH_SIZE = 10000  # Tune based on your document size


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
    parsed_date = parse_datetime_safe(date_str)
    if not parsed_date:
        return False

    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    start_date = datetime(year, 1, 1, tzinfo=pytz.UTC)

    return start_date <= parsed_date <= now

for collection_name in collections_list:
    logger.info(f"Processing: {collection_name}")
    
    source_collection = clientdb[collection_name]
    
    # Query with date filter (MongoDB does the filtering)
    query = {
        'time': {
            '$gte': start_date,
            '$lte': end_date
        }
    }
    
    # Use cursor with batch processing
    cursor = source_collection.find({}).batch_size(BATCH_SIZE)
    
    bulk_operations = []
    merged_count = 0
    
    for data in cursor:
        data_copy = data.copy()
        data_copy['source_collection'] = collection_name
        del data_copy['_id']
        
        details = data_copy.get('description',{}).get('details','')
        if not details : continue
        
        time = data_copy.get('time','')
        
        if time :
            if not is_date_within_year_range(time, year=2025): 
                continue
        
        unique_filter = {
            'source_collection': collection_name,
            'url': str(data['url'])
        }
        
        # Build bulk operation
        bulk_operations.append(
            UpdateOne(
                unique_filter,
                {'$set': data_copy},
                upsert=True
            )
        )
        
        # Execute in batches
        if len(bulk_operations) >= BATCH_SIZE:
            merged_collection.bulk_write(bulk_operations, ordered=False)
            merged_count += len(bulk_operations)
            logger.info(f"  Batch written: {merged_count} documents")
            bulk_operations = []
    
    # Write remaining operations
    if bulk_operations:
        merged_collection.bulk_write(bulk_operations, ordered=False)
        merged_count += len(bulk_operations)
    
    logger.info(f"{collection_name}: {merged_count} documents merged")

logger.info(f"Total documents in merged collection: {merged_collection.count_documents({})}")