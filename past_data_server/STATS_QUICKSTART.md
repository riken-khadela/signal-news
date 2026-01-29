# Statistics Tracking - Quick Reference

## What Was Added

✅ **stats_tracker.py** - Statistics tracking module  
✅ **z_main.py** - Integrated statistics tracking  
✅ **view_stats.py** - Utility to view statistics  
✅ **STATS_GUIDE.md** - Complete documentation  

## How It Works

Every time you run `python z_main.py`, the system automatically:

1. **Tracks the run** - Start time, end time, duration, mode
2. **Tracks each scraper** - Articles scraped, skipped, errors, duration
3. **Saves to JSON** - Appends to `scraper_stats.json`
4. **Calculates summary** - Total runs, articles, averages

## Quick Start

### Run Scrapers (Auto-saves stats)
```bash
python z_main.py
```

### View Statistics
```bash
python view_stats.py
```

### View JSON Directly
```bash
cat scraper_stats.json
```

## What Gets Saved

### Per Run:
- Run ID (timestamp)
- Start/end time
- Duration
- Mode (full/incremental)
- Total scrapers, successful, failed
- Total articles scraped/skipped
- Total errors

### Per Scraper:
- Status (success/failed)
- Start/end time
- Duration
- Articles scraped
- Articles skipped
- Errors
- Collection name
- Before/after article count
- Error message (if failed)

### Summary:
- Total runs all-time
- Total articles all-time
- Average duration
- Latest run details

## File Location

**scraper_stats.json** - Same directory as z_main.py

## Example Stats File

```json
{
  "runs": [
    {
      "run_id": "20260128_112430",
      "start_time": "2026-01-28T11:24:30+05:30",
      "end_time": "2026-01-28T11:45:15+05:30",
      "duration_seconds": 1245.67,
      "mode": "incremental",
      "total_scrapers": 32,
      "successful_scrapers": 30,
      "failed_scrapers": 2,
      "total_articles_scraped": 245,
      "total_articles_skipped": 1523,
      "total_errors": 3,
      "scrapers": {
        "tech_crunch": {
          "status": "success",
          "articles_scraped": 15,
          "articles_skipped": 45,
          "duration_seconds": 97.5,
          "collection": "news_details"
        }
        // ... all scrapers
      }
    }
    // ... previous runs
  ],
  "summary": {
    "total_runs": 15,
    "total_articles_scraped": 3456,
    "average_duration_seconds": 1234.56
  }
}
```

## Benefits

✅ Track performance over time  
✅ Identify slow scrapers  
✅ Monitor error rates  
✅ Analyze efficiency (skip ratios)  
✅ Historical data for reporting  
✅ Debug with saved error messages  

## See Also

- **STATS_GUIDE.md** - Complete documentation
- **stats_tracker.py** - Implementation details
- **view_stats.py** - Viewing utility source
