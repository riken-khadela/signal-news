from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from news_scrapper.tech_funding_news import TechFundingNews
from news_scrapper.tech_crunch import TechCrunch
from news_scrapper.your_story import YourStory
from news_scrapper.inc42 import Inc42

from logger import CustomLogger

logger = CustomLogger('/home/riken/news-scrapper/news-scrapper/log/main')


def news_scrapper(max_workers = 6):

    tasks = [
        TechFundingNews().run,
        TechCrunch().run,
        YourStory().run,
        Inc42().run,
    ]


    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(task): task.__qualname__
            for task in tasks
        }

        for future in as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                future.result()
                logger.info(f"✓ Completed: {task_name}")
            except Exception as e:
                logger.error(f"✗ Failed: {task_name} → {e}", exc_info=True)


if __name__ == "__main__":
    logging.info("[START] Script initialized...")
    news_scrapper(6)
    logging.info("[END] Script completed...")














# import threading
# import time
# import traceback
# import logging
# from news_scrapper.tech_funding_news import TechFundingNews
# from news_scrapper.tech_crunch import TechCrunch
# from news_scrapper.your_story import YourStory
# from news_scrapper.inc42 import Inc42
# from logger import CustomLogger
# import past_data.advance_materials
# import past_data.azonano
# import past_data.betakit
# import past_data.business_insider
# import past_data.canary
# import past_data.cleanenergywire
# import past_data.cnet
# import past_data.intelligence360
# import past_data.mining
# import past_data.neno_werk
# import past_data.next_web
# import past_data.quantam_insider
# import past_data.tech_eu
# import past_data.wired
# import past_data.zdnet
# logger = CustomLogger('/home/riken/news-scrapper/news-scrapper/log/main')

# def news_scrapper():
#     TechFundingNews().run()
#     TechCrunch().run()
#     YourStory().run()
#     Inc42().run()   
#     past_data.azonano.main()
#     past_data.advance_materials.AdvanceMaterials.run()
#     past_data.betakit.BetaKit.run()
#     past_data.business_insider.BusinessInsider.run()
#     past_data.canary.Canary.run()
#     past_data.cleanenergywire.CleanEnergyWire.run()
#     past_data.cnet.Cnet.run()
#     past_data.intelligence360.Inteligence360.run()
#     past_data.mining.Mining.run()
#     past_data.neno_werk.NanoWerk.run()
#     past_data.next_web.NextWeb.run()
#     past_data.quantam_insider.QuantamInsider.run()
#     past_data.tech_eu.TechEu.run()
#     past_data.wired.Wired.run()
#     past_data.zdnet.Zdnet.run()

# if __name__ == "__main__":
#     logging.info("[START] Script initialized...")
#     news_scrapper()
#     logging.info("[END] Script completed...")





# from link_scrapper.main import main as link_scrapper
# from news_scrapper.main import main as news_scrapper
# import threading
# import time
# import traceback


# def run_cycle_for_4_hours():
#     start_time = time.time()
#     run_duration = 4 * 60 * 60  # 4 hours in seconds

#     while time.time() - start_time < run_duration:
#         try:
#             t1 = threading.Thread(target=link_scrapper)
#             t2 = threading.Thread(target=news_scrapper)

#             t1.start()
#             t2.start()

#             t1.join()
#             t2.join()

#             print("[INFO] One iteration complete. Sleeping for 10 seconds before next iteration...")
#             time.sleep(10)

#         except Exception as e:
#             print("[ERROR] Exception occurred:", e)
#             traceback.print_exc()
#             time.sleep(60)  # Wait 1 minute before retrying on error

# if __name__ == "__main__":
#     print("[START] Script initialized...")

#     while True:
#         print("[INFO] Starting 4-hour active cycle...")
#         run_cycle_for_4_hours()

#         print("[INFO] 4-hour cycle complete. Now sleeping for 4 hours...")
#         time.sleep(4 * 60 * 60)  
