"""
View Scraper Statistics
========================
Simple utility to view and analyze scraper statistics from scraper_stats.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from tabulate import tabulate


def load_stats(stats_file="scraper_stats.json"):
    """Load statistics from JSON file"""
    if not Path(stats_file).exists():
        print(f"❌ Stats file not found: {stats_file}")
        print("Run z_main.py first to generate statistics.")
        return None
    
    with open(stats_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_summary(data):
    """Print overall summary"""
    summary = data.get("summary", {})
    
    print("\n" + "="*80)
    print("📊 OVERALL STATISTICS SUMMARY")
    print("="*80)
    print(f"Total Runs: {summary.get('total_runs', 0)}")
    print(f"Total Articles Scraped: {summary.get('total_articles_scraped', 0):,}")
    print(f"Total Errors: {summary.get('total_errors', 0)}")
    print(f"Average Duration: {summary.get('average_duration_seconds', 0):.2f} seconds")
    print(f"\nLatest Run:")
    print(f"  - Run ID: {summary.get('latest_run_id', 'N/A')}")
    print(f"  - Time: {summary.get('latest_run_time', 'N/A')}")
    print(f"  - Articles: {summary.get('latest_run_articles', 0)}")
    print("="*80)


def print_latest_run(data):
    """Print details of latest run"""
    runs = data.get("runs", [])
    if not runs:
        print("\n❌ No runs found")
        return
    
    latest = runs[-1]
    
    print("\n" + "="*80)
    print("🔥 LATEST RUN DETAILS")
    print("="*80)
    print(f"Run ID: {latest.get('run_id')}")
    print(f"Start Time: {latest.get('start_time')}")
    print(f"End Time: {latest.get('end_time')}")
    print(f"Duration: {latest.get('duration_seconds', 0):.2f} seconds")
    print(f"Mode: {latest.get('mode')}")
    print(f"\nResults:")
    print(f"  - Total Scrapers: {latest.get('total_scrapers', 0)}")
    print(f"  - Successful: {latest.get('successful_scrapers', 0)}")
    print(f"  - Failed: {latest.get('failed_scrapers', 0)}")
    print(f"  - Articles Scraped: {latest.get('total_articles_scraped', 0)}")
    print(f"  - Articles Skipped: {latest.get('total_articles_skipped', 0)}")
    print(f"  - Errors: {latest.get('total_errors', 0)}")
    print("="*80)


def print_scraper_details(data, limit=10):
    """Print details for each scraper from latest run"""
    runs = data.get("runs", [])
    if not runs:
        return
    
    latest = runs[-1]
    scrapers = latest.get("scrapers", {})
    
    if not scrapers:
        print("\n❌ No scraper details found")
        return
    
    print("\n" + "="*80)
    print(f"📋 SCRAPER DETAILS (Top {limit} by articles)")
    print("="*80)
    
    # Sort by articles scraped
    sorted_scrapers = sorted(
        scrapers.items(),
        key=lambda x: x[1].get("articles_scraped", 0),
        reverse=True
    )[:limit]
    
    # Prepare table data
    table_data = []
    for name, stats in sorted_scrapers:
        table_data.append([
            name,
            "✅" if stats.get("status") == "success" else "❌",
            stats.get("articles_scraped", 0),
            stats.get("articles_skipped", 0),
            stats.get("errors", 0),
            f"{stats.get('duration_seconds', 0):.1f}s",
            stats.get("collection", "N/A")
        ])
    
    headers = ["Scraper", "Status", "Scraped", "Skipped", "Errors", "Duration", "Collection"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print("="*80)


def print_failed_scrapers(data):
    """Print failed scrapers from latest run"""
    runs = data.get("runs", [])
    if not runs:
        return
    
    latest = runs[-1]
    scrapers = latest.get("scrapers", {})
    
    failed = {name: stats for name, stats in scrapers.items() 
              if stats.get("status") != "success"}
    
    if not failed:
        print("\n✅ No failed scrapers in latest run!")
        return
    
    print("\n" + "="*80)
    print("❌ FAILED SCRAPERS")
    print("="*80)
    
    for name, stats in failed.items():
        print(f"\n{name}:")
        print(f"  Duration: {stats.get('duration_seconds', 0):.2f}s")
        error_msg = stats.get("error_message", "No error message")
        print(f"  Error: {error_msg}")
    
    print("="*80)


def print_run_history(data, limit=5):
    """Print history of recent runs"""
    runs = data.get("runs", [])
    if not runs:
        return
    
    print("\n" + "="*80)
    print(f"📅 RUN HISTORY (Last {limit} runs)")
    print("="*80)
    
    table_data = []
    for run in reversed(runs[-limit:]):
        table_data.append([
            run.get("run_id", "N/A"),
            run.get("start_time", "N/A")[:19],  # Trim to datetime only
            run.get("mode", "N/A"),
            f"{run.get('successful_scrapers', 0)}/{run.get('total_scrapers', 0)}",
            run.get("total_articles_scraped", 0),
            f"{run.get('duration_seconds', 0):.1f}s"
        ])
    
    headers = ["Run ID", "Start Time", "Mode", "Success", "Articles", "Duration"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print("="*80)


def main():
    """Main entry point"""
    stats_file = "scraper_stats.json"
    
    # Check if custom file provided
    if len(sys.argv) > 1:
        stats_file = sys.argv[1]
    
    # Load data
    data = load_stats(stats_file)
    if not data:
        return
    
    # Print all sections
    print_summary(data)
    print_latest_run(data)
    print_scraper_details(data, limit=15)
    print_failed_scrapers(data)
    print_run_history(data, limit=5)
    
    print(f"\n💾 Stats file: {Path(stats_file).absolute()}")
    print(f"📊 Total runs recorded: {len(data.get('runs', []))}\n")


if __name__ == "__main__":
    main()
