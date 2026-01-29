import os
from pymongo import MongoClient, UpdateOne
from datetime import datetime
from dateutil import parser
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin9:i38kjmx35@94.130.33.235:27017/?authSource=admin&authMechanism=SCRAM-SHA-256&readPreference=primary&tls=true&tlsAllowInvalidCertificates=true&directConnection=true"
)

client = MongoClient(MONGO_URI, maxPoolSize=50)
clientdb = client.NEWSSCRAPERDATA

collections_list = [
    "new_details", "intelligence360", "THE_WIRED", "ZDNET", "BETA_KIT",
    "BUSINESSINSIDER", "TECH_EU", "TEST_NEXT_WEB", "CANARY",
    "CLEANENERGY_WIRE", "ADVANCE_MATERIALS_MAGAZINE", "THE_QUANTUM_INSIDER",
    "CNET", "MINING", "NANOWERK", "AZONANO", "RIGZONE", "PHOCUSWIRE",
    "TECHINASIA", "CLEANTECHCHINA", "HTN_CO_UK", "HEALTHTECHASIA", "WORLDOIL",
    "RENEWABLEENERGYWORLD", "MobileHealthNews", "HEALTHTECHMAGAZINE", "FORTUNE",
    "COMPLIANCEWEEK", "CRUNCHBASE", "SACRA", "HEALTHCAREASIAMAGAZINE",
    "MERGED_NEWS"
]

BATCH_SIZE = 5000  # Reduced for faster commits

def convert_date_obj(value):
    if not value:
        value = "01-01-2025"
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = parser.parse(str(value), fuzzy=True)
        return dt.astimezone(pytz.UTC) if dt.tzinfo else dt.replace(tzinfo=pytz.UTC)
    except Exception:
        return None

def fix_data_doc(data_doc):
    template = {
        "author": "",
        "image": "",
        "url": "",
        "title": "",
        "time": "",
        "description": {
            "summary": "",
            "details": ""
        }
    }
    
    # Start with a copy of the original data to preserve extra keys
    fixed_doc = data_doc.copy()
    
    # Ensure all required top-level keys exist
    for key in ["author", "image", "url", "title", "time"]:
        if key not in fixed_doc:
            fixed_doc[key] = template[key]
    
    # Handle the nested 'description' key
    if "description" not in fixed_doc or not isinstance(fixed_doc["description"], dict):
        fixed_doc["description"] = template["description"].copy()
    else:
        # Ensure both summary and details exist in description
        if "summary" not in fixed_doc["description"]:
            fixed_doc["description"]["summary"] = ""
        if "details" not in fixed_doc["description"]:
            fixed_doc["description"]["details"] = ""
    
    return fixed_doc

def process_collection(collection_name):
    print(f"\n▶ Processing: {collection_name}")
    collection = clientdb[collection_name]
    
    # Only fetch _id, url, and time - don't load entire docs
    cursor = collection.find({}).batch_size(BATCH_SIZE)
    
    bulk_ops = []
    updated = 0
    
    for doc in cursor:
        data_copy = fix_data_doc(doc)

        bulk_ops.append(
            UpdateOne(
                {"_id": doc["_id"]},  # Use _id for faster lookups
                {"$set": data_copy}
            )
        )
        
        if len(bulk_ops) >= BATCH_SIZE:
            collection.bulk_write(bulk_ops, ordered=False)
            updated += len(bulk_ops)
            print(f"  {collection_name}: {updated} updated")
            bulk_ops = []
    
    if bulk_ops:
        collection.bulk_write(bulk_ops, ordered=False)
        updated += len(bulk_ops)
    
    print(f"✔ {collection_name}: {updated} total")
    return collection_name, updated

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process_collection, name): name for name in collections_list}
    
    for future in as_completed(futures):
        try:
            name, count = future.result()
        except Exception as e:
            print(f"✘ {futures[future]} FAILED: {e}")

print("\n✔ ALL DONE")