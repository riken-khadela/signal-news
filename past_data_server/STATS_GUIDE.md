# Statistics Tracking System

The scraper system now automatically saves comprehensive statistics to `scraper_stats.json` after each run.

## What Gets Tracked

### Per Run:
- **Run ID** - Unique identifier (timestamp-based)
- **Start/End Time** - When the run started and completed
- **Duration** - Total time taken in seconds
- **Mode** - Full or incremental scraping
- **Overall Stats**:
  - Total scrapers run
  - Successful vs failed scrapers
  - Total articles scraped
  - Total articles skipped
  - Total errors

### Per Scraper (in each run):
- **Status** - Success or failed
- **Start/End Time** - When the scraper started and completed
- **Duration** - Time taken in seconds
- **Articles Scraped** - New articles added
- **Articles Skipped** - Existing articles skipped
- **Errors** - Number of errors encountered
- **Collection** - MongoDB collection name
- **Before/After Count** - Article count before and after scraping
- **Error Message** - First 200 chars of error (if failed)

### Summary Statistics:
- Total runs across all time
- Total articles scraped across all runs
- Total errors across all runs
- Average duration per run
- Latest run details

## File Location

**Path:** `scraper_stats.json` (in the same directory as `z_main.py`)

## File Structure

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
          "start_time": "2026-01-28T11:24:35+05:30",
          "end_time": "2026-01-28T11:26:12+05:30",
          "duration_seconds": 97.5,
          "articles_scraped": 15,
          "articles_skipped": 45,
          "errors": 0,
          "collection": "news_details",
          "before_count": 1234,
          "after_count": 1249,
          "error_message": ""
        },
        "wired": {
          "status": "success",
          "start_time": "2026-01-28T11:24:36+05:30",
          "end_time": "2026-01-28T11:27:45+05:30",
          "duration_seconds": 189.2,
          "articles_scraped": 23,
          "articles_skipped": 67,
          "errors": 0,
          "collection": "THE_WIRED",
          "before_count": 5678,
          "after_count": 5701,
          "error_message": ""
        }
        // ... all other scrapers
      }
    }
    // ... previous runs
  ],
  "summary": {
    "total_runs": 15,
    "total_articles_scraped": 3456,
    "total_errors": 12,
    "average_duration_seconds": 1234.56,
    "latest_run_id": "20260128_112430",
    "latest_run_time": "2026-01-28T11:24:30+05:30",
    "latest_run_articles": 245
  }
}
```

## Viewing Statistics

### Option 1: View Stats Script (Recommended)

```bash
python view_stats.py
```

This will display:
- Overall summary
- Latest run details
- Top scrapers by articles
- Failed scrapers (if any)
- Run history (last 5 runs)

### Option 2: Direct JSON File

```bash
# View entire file
cat scraper_stats.json

# View latest run only (using jq)
jq '.runs[-1]' scraper_stats.json

# View summary
jq '.summary' scraper_stats.json
```

### Option 3: Python Script

```python
from stats_tracker import StatsTracker

tracker = StatsTracker()

# Get summary
summary = tracker.get_summary()
print(summary)

# Get history for specific scraper
history = tracker.get_scraper_history("tech_crunch", limit=10)
for run in history:
    print(f"{run['run_time']}: {run['articles_scraped']} articles")
```

## Example Output

When you run `python view_stats.py`, you'll see:

```
================================================================================
📊 OVERALL STATISTICS SUMMARY
================================================================================
Total Runs: 15
Total Articles Scraped: 3,456
Total Errors: 12
Average Duration: 1234.56 seconds

Latest Run:
  - Run ID: 20260128_112430
  - Time: 2026-01-28T11:24:30+05:30
  - Articles: 245
================================================================================

================================================================================
🔥 LATEST RUN DETAILS
================================================================================
Run ID: 20260128_112430
Start Time: 2026-01-28T11:24:30+05:30
End Time: 2026-01-28T11:45:15+05:30
Duration: 1245.67 seconds
Mode: incremental

Results:
  - Total Scrapers: 32
  - Successful: 30
  - Failed: 2
  - Articles Scraped: 245
  - Articles Skipped: 1523
  - Errors: 3
================================================================================

================================================================================
📋 SCRAPER DETAILS (Top 15 by articles)
================================================================================
+-------------------+--------+---------+---------+--------+----------+------------------+
| Scraper           | Status | Scraped | Skipped | Errors | Duration | Collection       |
+===================+========+=========+=========+========+==========+==================+
| wired             | ✅     | 23      | 67      | 0      | 189.2s   | THE_WIRED        |
| tech_crunch       | ✅     | 15      | 45      | 0      | 97.5s    | news_details     |
| zdnet             | ✅     | 12      | 34      | 0      | 145.3s   | ZDNET            |
| ...               | ...    | ...     | ...     | ...    | ...      | ...              |
+-------------------+--------+---------+---------+--------+----------+------------------+
================================================================================
```

## Benefits

1. **Historical Tracking** - See trends over time
2. **Performance Analysis** - Identify slow scrapers
3. **Error Monitoring** - Track which scrapers fail most often
4. **Efficiency Metrics** - See skip ratios and article yields
5. **Debugging** - Error messages saved for later review
6. **Reporting** - Generate reports from JSON data

## Notes

- File is automatically created on first run
- Each run appends to the file (never overwrites)
- File size grows over time - consider archiving old runs periodically
- All times are in IST (Asia/Kolkata timezone)
- Statistics are saved even if the run is interrupted
