# Scraper Update Guide

## Overview

This guide shows how to update individual scrapers to work with the new unified management system (`z_main.py`) and leverage the `BaseScraper` class for improved functionality.

## What Changed

### Before (Old Scraper Pattern)
```python
class TechCrunch:
    def __init__(self):
        self.grid_details = []
        self.page_index = 1
        self.run_loop = True
        news_details_client.create_index("url", unique=True)
        self.skipped_urls = 0
    
    def run(self):
        while self.run_loop:
            # Scrape all pages
            # No skip threshold
            # No configuration support
            pass
```

### After (New Pattern with BaseScraper)
```python
from base_scraper import BaseScraper
from settings import news_details_client

class TechCrunch(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/tech_crunch"
        )
        self.grid_details = []
    
    def run(self):
        while self.should_continue_scraping():
            # Automatically respects:
            # - Page limits (incremental mode)
            # - Skip threshold
            # - Date filtering
            pass
```

## Step-by-Step Update Process

### Step 1: Import BaseScraper

**Add at top of file:**
```python
from base_scraper import BaseScraper
```

### Step 2: Inherit from BaseScraper

**Change class definition:**
```python
# Before
class YourScraper:
    def __init__(self):
        # ...

# After
class YourScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=YOUR_DB_CLIENT,  # e.g., THE_WIRED_client
            log_folder="log/your_scraper"
        )
        # Your custom initialization
```

### Step 3: Remove Duplicate Code

**Remove these (now in BaseScraper):**
```python
# ❌ Remove - handled by BaseScraper
self.page_index = 1
self.run_loop = True
self.skipped_urls = 0
self.logger = CustomLogger(...)
```

### Step 4: Update run() Method

**Replace while loop condition:**
```python
# Before
while self.run_loop:
    # ...

# After
while self.should_continue_scraping():
    # Automatically handles:
    # - run_loop flag
    # - Page limits
    # - Skip threshold
```

### Step 5: Use check_article_exists()

**Replace manual DB checks:**
```python
# Before
# if news_details_client.find_one({"url": grid["url"]}):
#     continue

# After
if self.check_article_exists(grid["url"]):
    continue  # Automatically tracks consecutive skips
```

### Step 6: Use is_article_too_old()

**Add date filtering:**
```python
# After parsing article date
article_time = datetime.fromisoformat(date)

if self.is_article_too_old(article_time, cutoff_year=2025):
    continue  # Automatically sets run_loop=False
```

### Step 7: Use save_article()

**Replace manual update_one:**
```python
# Before
news_details_client.update_one(
    {"url": article_data['url']},
    {"$set": article_data},
    upsert=True
)

# After
if self.save_article(article_data):
    self.logger.info(f"✅ Saved: {article_data['title']}")
```

### Step 8: Log Statistics

**Add at end of run():**
```python
def run(self):
    # ... scraping logic ...
    
    # Log final statistics
    self.log_stats()
```

## Complete Example: Updated TechCrunch Scraper

```python
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from bs4 import BeautifulSoup
from requests import RequestException
from settings import get_request, news_details_client
from base_scraper import BaseScraper
import pytz

ist = pytz.timezone("Asia/Kolkata")
URL = "https://techcrunch.com/latest/page/"

class TechCrunch(BaseScraper):
    def __init__(self):
        super().__init__(
            db_client=news_details_client,
            log_folder="log/tech_crunch"
        )
        self.grid_details = []

    def get_grid_details(self):
        \"\"\"Scrape the grid (listing) page.\"\"\"
        try:
            done, response = get_request(URL + str(self.page_index))
            if not done:
                self.logger.error(f"Request failed: {URL}")
                return []

            self.grid_details = self.scrape_grid_data(response.text)
            self.logger.info(f"Collected {len(self.grid_details)} grid items.")
            return self.grid_details

        except Exception as e:
            self.logger.error(f"Error in get_grid_details: {e}")
            return []

    def scrape_grid_data(self, html_content):
        \"\"\"Extract article data from page\"\"\"
        data = BeautifulSoup(html_content, 'html.parser')
        articles = [i for i in data.find_all('li', {'class': 'post'}) if i.find('img')]
        
        extracted_data = []
        for article in articles:
            try:
                # Extract data
                title_span = article.find('h3')
                if not title_span:
                    continue
                
                article_url = title_span.find('a').get('href', '')
                title = title_span.get_text(strip=True)
                
                # Check if exists (with skip tracking)
                if self.check_article_exists(article_url):
                    continue
                
                # Extract date
                date_span = article.find('time')
                date = date_span.get('datetime', '') if date_span else ''
                
                # Check if too old
                if date:
                    article_time = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    if self.is_article_too_old(article_time, cutoff_year=2025):
                        break  # Stop processing this page
                
                # Extract other fields
                img_tag = article.find('img')
                image_url = img_tag.get('src', '') if img_tag else ''
                
                category_span = article.find('div', class_='loop-card__cat-group')
                category = category_span.get_text(strip=True) if category_span else ''
                
                article_data = {
                    'title': title,
                    'url': article_url,
                    'time': date,
                    'image': image_url,
                    'category': category
                }
                
                extracted_data.append(article_data)
                
            except Exception as e:
                self.logger.error(f"Error parsing article: {e}")
                continue
        
        return extracted_data

    def parse_blog_details(self, url):
        \"\"\"Parse individual article details\"\"\"
        try:
            done, response = get_request(url)
            if not done:
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article content
            content_div = soup.find('div', class_='article-content')
            if not content_div:
                return {}
            
            details = content_div.get_text(strip=True)
            
            return {
                'details': details
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing blog details: {e}")
            return {}

    def run(self):
        \"\"\"Main execution logic\"\"\"
        self.logger.info("🚀 Starting TechCrunch scraper")
        
        while self.should_continue_scraping():
            self.logger.info(f"📄 Processing page {self.page_index}")
            
            # Get grid details
            grid_details = self.get_grid_details()
            
            if not grid_details:
                self.logger.warning("No articles found, stopping")
                break
            
            # Process each article
            for grid in grid_details:
                try:
                    # Parse full article
                    blog_details = self.parse_blog_details(grid['url'])
                    
                    # Combine data
                    article_data = {
                        **grid,
                        'description': blog_details,
                        'scraped_at': datetime.now(ist).isoformat()
                    }
                    
                    # Save article (handles duplicate check)
                    if self.save_article(article_data):
                        self.logger.info(f"✅ Saved: {article_data['title'][:50]}...")
                    
                except Exception as e:
                    self.logger.error(f"Error processing article: {e}")
                    continue
            
            self.page_index += 1
            time.sleep(1)  # Rate limiting
        
        # Log final statistics
        self.log_stats()
        self.logger.info("✅ TechCrunch scraper completed")

def main():
    scraper = TechCrunch()
    scraper.run()

if __name__ == "__main__":
    main()
```

## Benefits of Using BaseScraper

✅ **Automatic Skip Tracking** - Stops after 10 consecutive duplicates  
✅ **Page Limits** - Respects max_pages in incremental mode  
✅ **Date Filtering** - Automatically stops on old articles (< 2025-01-01)  
✅ **Configuration Support** - Receives config from z_main.py  
✅ **Standardized Logging** - Consistent log format across scrapers  
✅ **Statistics Tracking** - Automatic stats collection and reporting  
✅ **Less Code** - Removes 50+ lines of boilerplate per scraper  

## Migration Checklist

For each scraper file:

- [ ] Import `BaseScraper`
- [ ] Inherit from `BaseScraper`
- [ ] Call `super().__init__()` with correct DB client
- [ ] Remove duplicate code (page_index, run_loop, logger, etc.)
- [ ] Replace `while self.run_loop:` with `while self.should_continue_scraping():`
- [ ] Use `check_article_exists()` instead of manual DB checks
- [ ] Use `is_article_too_old()` for date filtering
- [ ] Use `save_article()` instead of manual update_one
- [ ] Add `self.log_stats()` at end of run()
- [ ] Test the scraper

## Testing

After updating a scraper:

```bash
# Test individual scraper
python your_scraper.py

# Test with z_main.py
python z_main.py
```

Check logs for:
- ✅ Configuration received
- ✅ Skip threshold working
- ✅ Page limits respected
- ✅ Statistics logged

## Notes

- **Backward Compatible**: Scrapers without `set_config()` still work
- **Optional**: You can update scrapers gradually
- **Flexible**: Override BaseScraper methods as needed
