from email.mime import image
import logging
import time
from datetime import datetime
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, get_scrape_do_requests, ReNewableEnergyWorld_client as news_details_client, yourstory_scrape_do_requests, get_proxy
from datetime import datetime
from logger import CustomLogger
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import re

import requests

import requests

url = "https://pitchbook.com/news/reports?f1=00000198-7f4a-d7d3-a1bc-ffdb83d20000&p=4"

payload = {}
headers = {
  'accept': '*/*',
  'accept-language': 'en-US,en;q=0.9',
  'priority': 'u=1, i',
  'referer': 'https://pitchbook.com/news/reports?f1=00000198-7f4a-d7d3-a1bc-ffdb83d20000',
  'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
  'Cookie': 'sourceType=DIRECT; sourceUrl=; _mkto_trk=id:942-MYM-356&token:_mch-pitchbook.com-fda7e88d24d614725284654ae0cee32; _switch_session_id=1c60227a-5226-4876-bba4-26e066e9741e; OptanonAlertBoxClosed=2026-01-26T08:46:14.470Z; __cf_bm=jLopR8iSaSiqj3LQ0BnDSiZ1skkJNM8VUq1OU6dicRw-1769422579-1.0.1.1-DaCRkaVt8UVK9Zk3g7QaVXMTvWnk5EAdJTAwJ4T991cmZFBOe7CJUOO46RHiidRK6lEQ_4ujuQK4SpqjnyGY5zoenIWcK8wkLCaNh.5ZL5w; OptanonConsent=isGpcEnabled=0&datestamp=Mon+Jan+26+2026+15%3A48%3A43+GMT%2B0530+(India+Standard+Time)&version=202511.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=8b24c56b-c069-41d4-ac59-7810f978add7&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A0%2CC0002%3A0%2CC0003%3A0&intType=3&geolocation=IN%3BGJ&AwaitingReconsent=false; __cf_bm=xYPRoprP8au82cMd2XCREFKfMJcJHAUfiRQvMU5DHi8-1769422873-1.0.1.1-S5i59qBUvq9suKFo4h2.njc8eToXasABCIRZGRZR0zNX6L6I18EhTdjILUuPBia9KqHDtzNIazeEbGLLMDdG.x7MzCF.ICzj2ZBt2m1KS30'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text[:100])
