from bs4 import BeautifulSoup
import datetime
import requests
from fake_useragent import UserAgent
import urllib.parse
import settings as cf
import logging, os, urllib3
import glob
from urllib.parse import unquote

from settings import proxies, logger as get_logger  # assuming `proxies()` and `logger()` are in settings.py
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_google_search_results(search_term, site_name, time='w', country_code='US'):
    logger = get_logger(site_name)  # dynamically get site-specific logger (combined log file)

    if time not in ['d', 'w', 'm', 'y']:
        raise ValueError("Invalid time parameter. Use 'd', 'w', 'm', or 'y'.")
    if not site_name or not search_term or not search_term.strip():
        raise ValueError("Site name and search term must be non-empty.")

    search_term = search_term.strip()

    try:
        headers = {"User-Agent": UserAgent().random}
        query = f"{search_term} site:{site_name}"
        params = {"q": query,"tf": f"pm",}
        search_url = f"https://search.brave.com/search?{urllib.parse.urlencode(params)}"
        response = requests.get(search_url, headers=headers, timeout=10, proxies=proxies())
        logger.info("Response status code: %s", response.status_code)
        if response.status_code == 200:
            logger.info("Fetched results for: %s", search_term)

            return response.text

    except Exception as e:
        logger.error("Exception during Google Search fetch: %s", str(e))

    return None

def clean_google_url(href: str) -> str:
    if href.startswith("/url?q="):
        href = unquote(href.split("/url?q=")[-1].split("&")[0])
    return href

def requests_next_page(url, site_name, logger):
    headers = {"User-Agent": UserAgent().random}
    try:
        response = requests.get(url, headers=headers, timeout=10, proxies=proxies())
        if response.status_code == 200:
            logger.info("Fetched next page: %s", url)
            return response.text
        else:
            logger.error("Failed to fetch next page. Status code: %s", response.status_code)
    except Exception as e:
        logger.error("Exception during next page fetch: %s", str(e))
    return None

def get_next_page_url(html):
    soup = BeautifulSoup(html, 'lxml')
    pagination_div = soup.find('div', {'id': 'pagination'})
    if pagination_div:
        next_page = pagination_div.find('a')
        if next_page:
            next_page_path = next_page.get('href')
            if next_page_path:
                full_url = urllib.parse.urljoin("https://search.brave.com", next_page_path)
                print(f"Next page URL: {full_url}")
                return full_url
    return None

def get_data_from_page(html, key_data, tag, search_term, site_name, logger, index=0):
    data = BeautifulSoup(html, 'lxml')
    extracted_links = []
    result_div = data.find('div',{'id':'results'})
    for result in result_div.find_all('div',{'class':'snippet'}) :
        href = ""
        result_title = ""
        if result.find('a') and result.find('div',{'class':'title'}):
            result_href = result.find('a').get('href')
            result_title = result.find('div',{'class':'title'}).text
            if not result_href or not result_title:
                continue
            href = clean_google_url(result_href)
        if not href or site_name not in href:
            continue
        elif href == f"https://www.{site_name}/" or href == f"https://{site_name}/" or f"https://www.{site_name}/latest/" in href or f"https://{site_name}/latest/" in href:
            continue
        elif href.startswith("/url?q") or href.startswith("/search?q"):  
            continue

        print(f"Collected URL: {href}")
        index += 1
        obj = {
            "sector": key_data["sector"],
            "tag": tag,
            "search_string": search_term,
            "url": href,
            "title": result_title.strip(),
            "pub_date": datetime.datetime.now().replace(hour=0, minute=0, second=0),
            "created_at": datetime.datetime.now(),
            "is_read": 0,
            "status": "pending",
            "index": index,
            "google_page": 1,
            "count": 1
        }
        
        extracted_links.append(obj)
        logger.info("Collected URL: %s", href)

    if not extracted_links:
        logger.warning("No valid links extracted for search: %s", search_term)

    return extracted_links
    return soup

def parse_google_results(html, key_data, tag, search_term, site_name, logger ):
    extracted_links = []
    index = 0
    
    while True:
        data = ""
        next_page_url = ""
        links = ""
        data = BeautifulSoup(html, 'lxml')
        result_div = data.find('div',{'id':'results'})
        if not result_div:
            logger.warning("No results found in the HTML.")
            break
        
        index += 1
        logger.info("Processing page %d for search term: %s", index, search_term)
        links = get_data_from_page(html, key_data, tag, search_term, site_name, logger, index)
        extracted_links.extend(links)
        
        next_page_url = get_next_page_url(html)
        if not next_page_url:
            logger.info("No more pages to process.")
            break
        elif "offset=0" in next_page_url:
            logger.info("Reached the end of pagination.")
            break

        html = requests_next_page(next_page_url, site_name, logger)
        if not html:
            logger.warning("Failed to fetch next page HTML.")
            break
        
    print(f"Total links extracted: {len(extracted_links)}")
    return extracted_links
        