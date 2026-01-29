from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import InsertOne
import logging
from datetime import datetime
import pytz
from pymongo import MongoClient, UpdateOne, InsertOne
from datetime import datetime
from dateutil import parser
from logger import CustomLogger
import pytz

ist = pytz.timezone("Asia/Kolkata")
ist_time = datetime.now(tz=ist)

MONGO_URI = "mongodb://admin9:i38kjmx35@localhost:27017/?authSource=admin&authMechanism=SCRAM-SHA-256&readPreference=primary&tls=true&tlsAllowInvalidCertificates=true&directConnection=true"
masterclient = MongoClient(MONGO_URI)
clientdb = masterclient.NEWSSCRAPERDATA
merged_collection = clientdb.MERGED_NEWS
# Configuration
MAX_WORKERS = 10 
BATCH_SIZE = 5000  # Increased for better throughput
logger = CustomLogger('/home/riken/news-scrapper/news-scrapper/past_data/Logs/Merge2')



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

types_list = []
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
    else:
        global types_list
        types_list.append(type(date_str)) if type(date_str) not in types_list else None

    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    start_date = datetime(year, 1, 1, tzinfo=pytz.UTC)
    within_year = start_date <= parsed_date <= now
    return within_year


def process_single_collection(collection_name: str) -> dict:
    """Process one collection - designed for parallel execution"""
    try:
        source_collection = clientdb[collection_name]
        
        # 1. OPTIMIZED QUERY - Project only needed fields, filter in MongoDB
        projection = {
            '_id': 0,  # Exclude _id from the start
            'url': 1,
            'description.details': 1,
            'time': 1
            # Add other fields you need
        }
        
        # Filter in MongoDB, not Python
        query = {
            'description.details': {'$exists': True, '$ne': ''},
            'time': {'$exists': True}
        }
        
        # Use aggregation pipeline for better performance
        pipeline = [
            {'$match': query},
            {'$project': projection},
            {
                '$addFields': {
                    'source_collection': collection_name,
                    'updated_at': ist_time
                }
            }
        ]
        
        cursor = source_collection.aggregate(pipeline, allowDiskUse=True)
        
        # 2. FILTER BY DATE IN MEMORY (only needed docs)
        data_list = []
        for doc in cursor:
            time_val = doc.get('time', '')
            if time_val and not is_date_within_year_range(time_val, year=2025):
                continue
            data_list.append(doc)
        
        if not data_list:
            return {
                'collection': collection_name,
                'merged': 0,
                'skipped': 0
            }
        
        # 3. BATCH CHECK EXISTING URLs (single query)
        urls = [doc['url'] for doc in data_list]
        
        # Use projection to only get URLs, not full documents
        existing_urls = set(
            doc['url'] for doc in merged_collection.find(
                {'url': {'$in': urls}},
                {'_id': 0, 'url': 1}
            )
        )
        
        # 4. BUILD BULK OPERATIONS (only new docs)
        bulk_operations = [
            InsertOne(doc) 
            for doc in data_list 
            if doc['url'] not in existing_urls
        ]
        
        # 5. EXECUTE BULK WRITE
        if bulk_operations:
            result = merged_collection.bulk_write(
                bulk_operations, 
                ordered=False,
                bypass_document_validation=True  # Skip validation for speed
            )
            inserted = result.inserted_count
        else:
            inserted = 0
        
        return {
            'collection': collection_name,
            'merged': inserted,
            'skipped': len(data_list) - inserted
        }
        
    except Exception as e:
        logger.error(f"Error processing {collection_name}: {e}")
        return {
            'collection': collection_name,
            'merged': 0,
            'skipped': 0,
            'error': str(e)
        }


def merge_collections_parallel(collections_list: list):
    """
    Parallel processing with proper error handling and progress tracking
    """
    total_merged = 0
    total_skipped = 0
    failed_collections = []
    
    # Create index on merged collection for faster lookups
    try:
        merged_collection.create_index('url', unique=True, background=True)
        logger.info("Ensured index on merged collection")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")
    
    # Process collections in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_collection = {
            executor.submit(process_single_collection, coll): coll 
            for coll in collections_list
        }
        
        # Process results as they complete
        for future in as_completed(future_to_collection):
            collection_name = future_to_collection[future]
            
            try:
                result = future.result()
                
                if 'error' in result:
                    failed_collections.append(collection_name)
                    logger.error(f"❌ {collection_name}: FAILED - {result['error']}")
                else:
                    total_merged += result['merged']
                    total_skipped += result['skipped']
                    logger.info(
                        f"✓ {collection_name}: "
                        f"{result['merged']} merged, "
                        f"{result['skipped']} skipped"
                    )
                    
            except Exception as e:
                failed_collections.append(collection_name)
                logger.error(f"❌ {collection_name}: Exception - {e}")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY:")
    logger.info(f"Total merged: {total_merged}")
    logger.info(f"Total skipped: {total_skipped}")
    logger.info(f"Failed collections: {len(failed_collections)}")
    if failed_collections:
        logger.info(f"Failed: {', '.join(failed_collections)}")
    logger.info(f"{'='*60}\n")
    
    return {
        'total_merged': total_merged,
        'total_skipped': total_skipped,
        'failed': failed_collections
    }


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
    

# Usage
if __name__ == "__main__":
    # Run parallel processing
    results = merge_collections_parallel(collections_list)
    print(types_list )