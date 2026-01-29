from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime
from advance_materials import AdvanceMaterials
from azonano import Azonano
from betakit import BetaKit
from business_insider import BusinessInsider
from canary import Canary
from cleanenergywire import CleanEnergyWire
from cleantechnica import CleanTechChina
from cnet import Cnet
from complianceweek import ComplianceWeek
from crunchbase import CrunchBase
from fortune import Fortune
from healthcareasiamagazine import HealthCareAsiaMagazine
from healthtechasia import HealthTechAsia
from healthtechmagazine import HealthTechMagazine
from htn_co_uk import HTN_CO_UK
from intelligence360 import Inteligence360
from mining import Mining
from mobihealthnews import MobileHealthNews
from neno_werk import NanoWerk
from next_web import NextWeb
from phocuswire import PhocusWire
from quantam_insider import QuantamInsider
from rigzone import RigZone
from sacra import Sacra
from tech_eu import TechEu
from tech_in_aisa import TechInAsia
from wired import Wired
from worldoil import WorldOil
from zdnet import Zdnet
from logger import CustomLogger
from settings import *
import pytz

ist = pytz.timezone("Asia/Kolkata")
current_ist_time = datetime.now(tz=ist)

class MainScrapper:
    def __init__(self):
        self.should_skip = False
        
        # db clients
        self.advance_materials_db_client = ADVANCE_MATERIALS_MAGAZINE_client
        self.azonano_db_client = AZONANO_client
        self.betakit_db_client = BETA_KIT_client
        self.business_insider_db_client = BUSINESSINSIDER_client
        self.canary_db_client = CANARY_client
        self.cleanenergywire_db_client = CLEANENERGY_WIRE_client
        self.cleantechnica_db_client = CLEANTECHCHINA_client
        self.cnet_db_client = CNET_client
        self.complianceweek_db_client = COMPLIANCEWEEK_client
        self.crunchbase_db_client = CRUNCHBASE_client
        self.fortune_db_client = FORTUNE_client
        self.healthcareasiamagazine_db_client = HEALTHCAREASIAMAGAZINE_client
        self.healthtechasia_db_client = HEALTHTECHASIA_client
        self.healthtechmagazine_db_client = HEALTHTECHMAGAZINE_client
        self.htn_co_uk_db_client = HTN_CO_UK_client
        self.intelligence360_db_client = intelligence360_client
        self.mining_db_client = MINING_client
        self.mobihealthnews_db_client = MobileHealthNews_client
        self.neno_werk_db_client = NANOWERK_client
        self.next_web_db_client = TEST_NEXT_WEB_client
        self.phocuswire_db_client = PHOCUSWIRE_client
        self.quantam_insider_db_client = THE_QUANTUM_INSIDER_client
        self.rigzone_db_client = RIGZONE_client
        self.sacra_db_client = SACRA_client
        self.tech_eu_db_client = TECH_EU_client
        self.tech_in_aisa_db_client = TECHINASIA_client
        self.wired_db_client = THE_WIRED_client
        self.worldoil_db_client = WORLDOIL_client
        self.zdnet_db_client = ZDNET_client
        
    
    def advance_materials(self):

        return {}

    def azonano(self):

        return {}

    def betakit(self):

        return {}

    def business_insider(self):

        return {}

    def canary(self):

        return {}

    def cleanenergywire(self):

        return {}

    def cleantechnica(self):

        return {}

    def cnet(self):

        return {}

    def complianceweek(self):

        return {}

    def crunchbase(self):

        return {}

    def fortune(self):

        return {}

    def healthcareasiamagazine(self):

        return {}

    def healthtechasia(self):

        return {}

    def healthtechmagazine(self):

        return {}

    def htn_co_uk(self):

        return {}

    def intelligence360(self):

        return {}

    def mining(self):

        return {}

    def mobihealthnews(self):

        return {}

    def neno_werk(self):

        return {}

    def next_web(self):

        return {}

    def phocuswire(self):

        return {}

    def quantam_insider(self):

        return {}

    def quantam_insider(self):

        return {}

    def rigzone(self):

        return {}

    def sacra(self):
        from sacra import logger
        URLS_LIST = [
            "https://sacra.com/explore/companies/"
        ]
        BASE_NEWS_URL = "https://sacra.com/explore/companies/"
        sacra_ = Sacra()
        data_list = []
        for url in URLS_LIST:
            sacra_.get_grid_details(url)
            if sacra_.grid_details:
                for grid in sacra_.grid_details :
                    for _ in range(3):
                        try:
                            if news_details_client.find_one({"url": grid["url"]}):
                                if self.should_skip :
                                    self.skipped_urls += 1
                                    continue

                            slug = grid["url"].rstrip("/").split("/")[-1]

                            details = sacra_.get_article_details(slug, grid)
                            if not details:
                                continue

                            merged = {**grid, **details}
                            if not merged.get('description',{}).get('details','') :
                                continue
                            merged['created_at'] = current_ist_time
                            data_list.append(merged)
                            # self.sacra_db_client.update_one( 
                            #     {"url": merged["url"]},
                            #     {"$set": merged},
                            #     upsert=True,
                            # )

                            # logger.info(f"Inserted: {merged['url']}")
                            time.sleep(1)
                            break

                        except Exception as e:
                            logger.error(f"Insert error: {e} in url : {grid['url']}")
        return data_list

    def tech_eu(self):

        return {}

    def tech_in_aisa(self):

        return {}

    def wired(self):

        return {}

    def worldoil(self):

        return {}

    def zdnet(self):

        return {}
