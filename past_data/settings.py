import logging
import os
import random
import time
import requests
import urllib3, urllib, json
from pymongo import MongoClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s - %(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler("log/main.log", mode="a"),
        logging.StreamHandler()
    ]
)

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin9:i38kjmx35@94.130.33.235:27017/?authSource=admin&authMechanism=SCRAM-SHA-256&readPreference=primary&tls=true&tlsAllowInvalidCertificates=true&directConnection=true"
)

masterclient = MongoClient(MONGO_URI)
clientdb = masterclient.NEWSSCRAPERDATA
news_details_client = clientdb.new_details
intelligence360_client = clientdb.intelligence360
THE_WIRED_client = clientdb.THE_WIRED
ZDNET_client = clientdb.ZDNET
BETA_KIT_client = clientdb.BETA_KIT
BUSINESSINSIDER_client = clientdb.BUSINESSINSIDER
NEXT_WEB_client = clientdb.NEXT_WEB
TECH_EU_client = clientdb.TECH_EU
TEST_NEXT_WEB_client = clientdb.TEST_NEXT_WEB
CANARY_client = clientdb.CANARY
CLEANENERGY_WIRE_client = clientdb.CLEANENERGY_WIRE
ADVANCE_MATERIALS_MAGAZINE_client = clientdb.ADVANCE_MATERIALS_MAGAZINE
THE_QUANTUM_INSIDER_client = clientdb.THE_QUANTUM_INSIDER
TECH_IN_ASIA_client = clientdb.TECH_IN_ASIA
TECH_EU_client = clientdb.TECH_EU
CNET_client = clientdb.CNET
MINING_client = clientdb.MINING
NANOWERK_client = clientdb.NANOWERK
AZONANO_client = clientdb.AZONANO
RIGZONE_client = clientdb.RIGZONE
PHOCUSWIRE_client = clientdb.PHOCUSWIRE
TECHINASIA_client = clientdb.TECHINASIA
CLEANTECHCHINA_client = clientdb.CLEANTECHCHINA
HTN_CO_UK_client = clientdb.HTN_CO_UK
HEALTHTECHASIA_client = clientdb.HEALTHTECHASIA
WORLDOIL_client = clientdb.WORLDOIL
ReNewableEnergyWorld_client = clientdb.RENEWABLEENERGYWORLD
MobileHealthNews_client = clientdb.MobileHealthNews
HEALTHTECHMAGAZINE_client = clientdb.HEALTHTECHMAGAZINE
FORTUNE_client = clientdb.FORTUNE
COMPLIANCEWEEK_client = clientdb.COMPLIANCEWEEK
CRUNCHBASE_client = clientdb.CRUNCHBASE
SACRA_client = clientdb.SACRA
HEALTHCAREASIAMAGAZINE_client = clientdb.HEALTHTECHMAGAZINE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
CONFIG_FILE = "/home/riken/news-scrapper/news-scrapper/config.json"
with open(CONFIG_FILE, "r") as f: config = json.load(f)
TOKEN = config["token"]

PROXIES = [
    "37.48.118.90:13082",
    "83.149.70.159:13082",
    "163.172.59.195:15003",
    "163.172.26.179:15003",
    "163.172.48.119:15003",
    "51.15.2.19:15003",
    "163.172.59.195:15004",
    "163.172.26.179:15004",
    "163.172.48.119:15004",
    "51.15.2.19:15004",
    "51.159.35.167:15003",
    "163.172.84.215:15003",
    "163.172.251.67:15003",
    "163.172.43.22:15003",
    "51.159.35.167:15004",
    "163.172.84.215:15004",
    "163.172.251.67:15004",
    "163.172.43.22:15004",
    "63.141.241.98:16001",
    "173.208.209.42:16001",
    "142.54.188.26:16001",
    "173.208.199.74:16001",
    "163.172.58.253:16001",
    "163.172.61.67:16001",
    "51.159.4.90:16001",
    "163.172.71.115:16001",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:116.0) Gecko/20100101 Firefox/116.0",
]

def get_proxy():
    prx = random.choice(PROXIES)
    return {"http": f"http://{prx}", "https": f"http://{prx}"}

def get_headers():
    return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            'x-requested-with': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        }

def random_sleep(start = 5, end = 10):
    time_sleep = random.randint(start, end)
    print(f'Time sleep for :', time_sleep, end=" ")
    time.sleep(time_sleep)

def get_request(url, max_retries=20, timeout=10, params = {}, headers = {}):
    """Perform GET request with retries, proxies, and UA rotation."""
    if not headers:
        headers = get_headers()
    for attempt in range(max_retries):
        try:
            res = requests.get(
                url,
                headers=headers,
                proxies=get_proxy(),
                timeout=timeout,
                verify=False,
                params=params
            )

            if res.status_code == 200:
                logging.info(f"✅ Success: {url} [{res.status_code}]")
                return True, res

            logging.warning(f"⚠️ Failed: {url} [{res.status_code}]")

        except requests.Timeout:
            logging.warning(f"⏳ Timeout on {url}, retry {attempt+1}/{max_retries}")
        except Exception as e:
            logging.warning(f"❌ Error fetching {url}: {e}")

        time.sleep(1)

    logging.error(f"❌ All retries failed for {url}")
    return False, None



def get_scrape_do_requests(url):
    c = 0
    headers = get_headers()

    while c < 10:
        try:
            encoded_url = urllib.parse.quote_plus(url)
            url = f"https://api.scrape.do/?token={TOKEN}&url={encoded_url}&render=true"
            res = requests.get(url, headers=headers, verify=False)
            print(f'scrape do URL: {res.url} : status code --> {res.status_code}',)

            if res.status_code == 200:
                return True, res

        except requests.Timeout:
            print("Request timed out. Retrying...")
        except requests.RequestException as e:
            print("Request failed: %s", e)

        print("Scrape do Checking try again: %d", c)
        time.sleep(0.5)
        c += 1

    return False, False


def yourstory_scrape_do_requests(url):
    c = 0
    headers = get_headers()
    waitSelector = ".container-results"
    render = "true"
    waitSelector = ".container-results li"
    
    while c < 10:
        try:
            encoded_url = urllib.parse.quote(url)
            url = f"http://api.scrape.do/?token={TOKEN}&url={encoded_url}&render={render}&waitSelector={waitSelector}"
            res = requests.get(url, headers=headers, verify=False)
            print(f'scrape do URL: {res.url} : status code --> {res.status_code}',)

            if res.status_code == 200:
                return True, res

        except requests.Timeout:
            print("Request timed out. Retrying...")
        except requests.RequestException as e:
            print("Request failed: %s", e)

        print("Scrape do Checking try again: %d", c)
        time.sleep(0.5)
        c += 1

    return False, False


def is_date_between_year_and_today(iso_timestamp: str, year: int):
    from datetime import datetime, timezone

    if not iso_timestamp or not year:
        return False

    try:
        parsed_date = datetime.fromisoformat(
            iso_timestamp.replace("Z", "+00:00")
        )

        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)

        return start_date <= parsed_date <= end_date

    except (ValueError, TypeError):
        return False