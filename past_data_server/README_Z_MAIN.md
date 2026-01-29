# Unified News Scraper System - README

## Overview

`z_main.py` is a comprehensive unified management system for all news scrapers. It provides centralized orchestration, configuration management, state tracking, and robust error handling.

## Features

✅ **Centralized Management** - Single file to run all 30+ scrapers  
✅ **Incremental Scraping** - Only fetch new articles after initial run  
✅ **Concurrent Execution** - Run multiple scrapers in parallel with thread pooling  
✅ **State Tracking** - Track last run time, success/failure stats per scraper  
✅ **Configuration Management** - Easy enable/disable scrapers without code changes  
✅ **Robust Error Handling** - Individual scraper failures don't stop the system  
✅ **Comprehensive Logging** - Detailed logs for debugging and monitoring  
✅ **Cron Job Ready** - Designed for automated 3x daily execution  

## Quick Start

### 1. Basic Usage

```bash
# Run all enabled scrapers
python z_main.py
```

### 2. Configuration

Edit `scraper_config.json` to customize behavior:

```json
{
  "mode": "incremental",          // "full" or "incremental"
  "max_workers": 6,                // Concurrent scrapers (1-10)
  "max_pages_per_scraper": 5,     // Pages per scraper in incremental mode
  "skip_existing": true,           // Skip articles already in DB
  "enabled_scrapers": "all",       // "all" or ["scraper1", "scraper2"]
  "disabled_scrapers": []          // List of scrapers to disable
}
```

### 3. Cron Job Setup

For 3x daily execution (8 AM, 2 PM, 8 PM):

```cron
0 8,14,20 * * * cd /path/to/news_scrapper/past_data_server && python z_main.py >> log/z_main/cron.log 2>&1
```

## File Structure

```
past_data_server/
├── z_main.py                  # Main orchestrator
├── scraper_config.json        # Configuration file
├── scraper_state.json         # State tracking (auto-generated)
├── log/z_main/                # Logs directory
│   ├── general.log
│   ├── info.log
│   ├── error.log
│   └── warning.log
└── [individual scraper files]
```

## Configuration Options

### Mode

- **`full`**: Scrape all available articles from each source (initial run)
- **`incremental`**: Only scrape recent articles (daily runs)

### Enabling/Disabling Scrapers

**Enable all scrapers:**
```json
{
  "enabled_scrapers": "all"
}
```

**Enable specific scrapers only:**
```json
{
  "enabled_scrapers": ["tech_crunch", "wired", "zdnet"]
}
```

**Disable specific scrapers:**
```json
{
  "enabled_scrapers": "all",
  "disabled_scrapers": ["sacra", "tech_in_aisa"]
}
```

## State Tracking

`scraper_state.json` automatically tracks:

- Last run timestamp
- Last successful run timestamp
- Total runs / successful runs / failed runs
- Total articles collected
- Last error message (if any)

Example state:
```json
{
  "tech_crunch": {
    "total_runs": 10,
    "successful_runs": 9,
    "failed_runs": 1,
    "total_articles": 450,
    "last_run": "2026-01-28T10:30:00+05:30",
    "last_success": "2026-01-28T10:30:00+05:30",
    "last_articles_count": 45
  }
}
```

## Monitoring

### Real-time Logs

Watch logs in real-time:
```bash
tail -f log/z_main/general.log
```

### Error Logs

Check for errors:
```bash
cat log/z_main/error.log
```

### Execution Summary

Each run prints a summary:
```
================================================================================
📈 EXECUTION SUMMARY
================================================================================
⏱️  Total Duration: 1234.56 seconds (20.58 minutes)
📊 Total Scrapers: 30
✅ Successful: 28
❌ Failed: 2
📰 Total Articles Collected: 1,234
⏰ End Time: 2026-01-28 10:45:30 IST
================================================================================
```

## Troubleshooting

### Scraper Fails

1. Check `log/z_main/error.log` for details
2. Check `scraper_state.json` for last error message
3. Run individual scraper directly to debug:
   ```python
   from tech_crunch import TechCrunch
   TechCrunch().run()
   ```

### Performance Issues

- Reduce `max_workers` in config (try 3-4)
- Increase `timeout_per_scraper` for slow scrapers
- Disable heavy scrapers (selenium-based) temporarily

### Database Connection Issues

- Verify MongoDB connection in `settings.py`
- Check network connectivity
- Ensure MongoDB is running

## Advanced Usage

### Custom Scraper Priority

Scrapers run based on priority (lower = higher priority):
- Priority 1: Standard pagination scrapers
- Priority 2: API-based scrapers
- Priority 3: Selenium-based scrapers (slower)

### Incremental Scraping Logic

In incremental mode:
1. System checks `scraper_state.json` for last successful run
2. Scrapers limit page iteration (max_pages_per_scraper)
3. Database check skips existing articles
4. Stops when encountering old articles

## Comparison with Old Systems

| Feature | main.py | s_main.py | z_main.py |
|---------|---------|-----------|-----------|
| Centralized Config | ❌ | ❌ | ✅ |
| State Tracking | ❌ | ❌ | ✅ |
| Incremental Mode | ❌ | ❌ | ✅ |
| Error Recovery | ❌ | ❌ | ✅ |
| Detailed Logging | ⚠️ | ⚠️ | ✅ |
| Easy Enable/Disable | ❌ | ❌ | ✅ |
| Cron Ready | ⚠️ | ⚠️ | ✅ |

## Migration Guide

### From main.py

Replace:
```bash
python main.py
```

With:
```bash
python z_main.py
```

### From s_main.py

1. Stop using `s_main.py`
2. Configure `scraper_config.json` as needed
3. Run `python z_main.py`

## Support

For issues or questions:
1. Check logs in `log/z_main/`
2. Review `scraper_state.json` for scraper-specific issues
3. Test individual scrapers directly
4. Check MongoDB connectivity and settings

## Future Enhancements

Potential improvements:
- [ ] Email notifications on failures
- [ ] Webhook integration for monitoring
- [ ] Dashboard for real-time status
- [ ] Automatic retry with exponential backoff
- [ ] Article deduplication across sources
- [ ] Performance metrics and analytics
