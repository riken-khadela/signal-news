# Quick Start Guide - z_main.py

## What is z_main.py?

A unified management system that runs all 30+ news scrapers from a single file with:
- ✅ Automatic incremental scraping (only new articles)
- ✅ Concurrent execution (6 scrapers at once)
- ✅ Error handling (one failure doesn't stop others)
- ✅ Easy configuration (no code changes needed)
- ✅ State tracking (knows what was scraped when)
- ✅ Cron job ready (for 3x daily automation)

---

## How to Use

### 1. Run It Now

```bash
cd c:\Workspace\Shushant\news_scrapper\past_data_server
python z_main.py
```

That's it! It will:
- Run all 30+ scrapers concurrently
- Skip articles already in database
- Log everything to `log/z_main/`
- Save state to `scraper_state.json`

### 2. Configure It (Optional)

Edit `scraper_config.json`:

```json
{
  "mode": "incremental",           // or "full" for first run
  "max_workers": 6,                 // how many scrapers run at once
  "enabled_scrapers": "all",        // or ["tech_crunch", "wired"]
  "disabled_scrapers": []           // scrapers to skip
}
```

### 3. Set Up Cron Job (For Automation)

For 3x daily execution (8 AM, 2 PM, 8 PM):

```bash
# Edit crontab
crontab -e

# Add this line:
0 8,14,20 * * * cd /path/to/news_scrapper/past_data_server && python z_main.py >> log/z_main/cron.log 2>&1
```

---

## What You Get

### Real-Time Progress

```
🎯 UNIFIED NEWS SCRAPER SYSTEM - STARTING
⏰ Start Time: 2026-01-28 10:30:00 IST
📋 Enabled Scrapers: 30

🚀 Starting scraper: tech_crunch
✅ tech_crunch completed successfully. Articles: 45
📊 Progress: 1/30 (✅ 1 | ❌ 0)
...
```

### Execution Summary

```
📈 EXECUTION SUMMARY
⏱️  Total Duration: 20.58 minutes
📊 Total Scrapers: 30
✅ Successful: 28
❌ Failed: 2
📰 Total Articles Collected: 1,234
```

### State Tracking

`scraper_state.json` tracks everything:

```json
{
  "tech_crunch": {
    "total_runs": 10,
    "successful_runs": 9,
    "total_articles": 450,
    "last_success": "2026-01-28T10:30:00+05:30"
  }
}
```

---

## Common Tasks

### Enable Only Specific Scrapers

Edit `scraper_config.json`:
```json
{
  "enabled_scrapers": ["tech_crunch", "wired", "zdnet"]
}
```

### Disable Slow Scrapers

```json
{
  "disabled_scrapers": ["sacra", "tech_in_aisa"]
}
```

### Check Logs

```bash
# All logs
cat log/z_main/general.log

# Errors only
cat log/z_main/error.log

# Watch in real-time
tail -f log/z_main/general.log
```

### Check What Was Scraped

```bash
cat scraper_state.json
```

---

## Troubleshooting

### Scraper Failed?

1. Check error log: `cat log/z_main/error.log`
2. Check state: `cat scraper_state.json`
3. Run scraper individually to debug

### Too Slow?

Reduce workers in `scraper_config.json`:
```json
{
  "max_workers": 3
}
```

### Need Full Scrape?

Change mode in `scraper_config.json`:
```json
{
  "mode": "full"
}
```

---

## Files Created

| File | Purpose |
|------|---------|
| `z_main.py` | Main orchestrator (600+ lines) |
| `scraper_config.json` | Configuration |
| `scraper_state.json` | Auto-generated state tracking |
| `README_Z_MAIN.md` | Full documentation |
| `log/z_main/` | Logs directory |

---

## Benefits Over Old System

| Feature | main.py | z_main.py |
|---------|---------|-----------|
| Incremental scraping | ❌ | ✅ |
| Easy enable/disable | ❌ | ✅ |
| State tracking | ❌ | ✅ |
| Error recovery | ❌ | ✅ |
| Detailed logging | ⚠️ | ✅ |
| Configuration file | ❌ | ✅ |

---

## Need Help?

1. Read full docs: `README_Z_MAIN.md`
2. Check logs: `log/z_main/`
3. Review state: `scraper_state.json`
4. Test individual scrapers

---

**That's it! You now have a professional, production-ready scraper management system.** 🚀
