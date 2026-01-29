import logging
import os, random

class SiteFilter(logging.Filter):
    def __init__(self, site_name):
        super().__init__()
        self.site_name = site_name

    def filter(self, record):
        record.site = self.site_name
        return True
    
def logger(site_name: str):
    log_file = "log/link_scrapper.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    log = logging.getLogger("link_scrapper")

    if not log.handlers:
        log.setLevel(logging.INFO)
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(site)s] %(message)s')
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

    # always add new site context filter
    log.addFilter(SiteFilter(site_name))
    return log


def check_log_file(file):
    """Create log file if it doesn't exist, including any missing parent directories."""
    
    dir_path = os.path.dirname(file)
    
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    
    if not os.path.exists(file):
        with open(file, 'w') as f:
            pass 

    return file


def proxies():
    plist = [
        "37.48.118.90:13082",
        "83.149.70.159:13082"
    ]
    prx = random.choice(plist)
    return {
        'http': 'http://' + prx,
        'https': 'http://' + prx
    }