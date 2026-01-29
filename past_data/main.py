from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

import advance_materials
import azonano
import betakit
import business_insider
import canary
import cleanenergywire
import cleantechnica
import cnet
import complianceweek
import crunchbase
import fortune
import healthcareasiamagazine
import healthtechasia
import healthtechmagazine
import htn_co_uk
import intelligence360
import mining
import mobihealthnews
import neno_werk
import next_web
import phocuswire
import quantam_insider
import rigzone
import sacra
import tech_eu
import tech_in_aisa
import wired
import worldoil
import zdnet
import logger

from logger import CustomLogger

logger = CustomLogger('/home/riken/news-scrapper/news-scrapper/past_data/Logs2/main')


def news_scrapper(max_workers = 25):

    tasks = [
        advance_materials.main,
        azonano.main,
        betakit.main,
        business_insider.main,
        canary.main,
        cleanenergywire.main,
        cleantechnica.main,
        cnet.main,
        complianceweek.main,
        crunchbase.main,
        fortune.main,
        healthcareasiamagazine.main,
        healthtechasia.main,
        healthtechmagazine.main,
        htn_co_uk.main,
        intelligence360.main,
        mining.main,
        mobihealthnews.main,
        neno_werk.main,
        next_web.main,
        phocuswire.main,
        quantam_insider.main,
        rigzone.main,
        sacra.main,
        tech_eu.main,
        tech_in_aisa.main,
        wired.main,
        worldoil.main,
        zdnet.main,
    ]


    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(task): task.__module__
            for task in tasks
        }

        for future in as_completed(futures):
            task_name = futures[future]
            try:
                future.result()
                logger.info(f"✓ Completed: {task_name}")
            except Exception as e:
                logger.error(
                    f"✗ Failed: {task_name} → {e}",
                    exc_info=True
                )

if __name__ == "__main__":
    logging.info("[START] Script initialized...")
    news_scrapper(6)
    logging.info("[END] Script completed...")
