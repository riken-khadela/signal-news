"""
Statistics Tracker for News Scraper System
Tracks and saves all scraper run statistics to JSON file
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path


class StatsTracker:
    """Track and save scraper statistics to JSON file"""
    
    def __init__(self, stats_file: str = "scraper_stats.json"):
        """
        Initialize stats tracker
        
        Args:
            stats_file: Path to JSON file for storing statistics
        """
        self.stats_file = stats_file
        self.current_run = {
            "run_id": None,
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0,
            "mode": "full",
            "total_scrapers": 0,
            "successful_scrapers": 0,
            "failed_scrapers": 0,
            "total_articles_scraped": 0,
            "total_articles_skipped": 0,
            "total_errors": 0,
            "scrapers": {}
        }
        
    def start_run(self, mode: str = "full", total_scrapers: int = 0):
        """
        Start a new scraper run
        
        Args:
            mode: Run mode (full/incremental)
            total_scrapers: Total number of scrapers to run
        """
        self.current_run = {
            "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_seconds": 0,
            "mode": mode,
            "total_scrapers": total_scrapers,
            "successful_scrapers": 0,
            "failed_scrapers": 0,
            "total_articles_scraped": 0,
            "total_articles_skipped": 0,
            "total_errors": 0,
            "scrapers": {}
        }
        
    def add_scraper_stats(self, scraper_name: str, stats: Dict[str, Any]):
        """
        Add statistics for a single scraper
        
        Args:
            scraper_name: Name of the scraper
            stats: Dictionary containing scraper statistics
                - status: "success" or "failed"
                - start_time: ISO format timestamp
                - end_time: ISO format timestamp
                - duration_seconds: Duration in seconds
                - articles_scraped: Number of new articles
                - articles_skipped: Number of skipped articles
                - errors: Number of errors
                - collection: Collection name
                - before_count: Article count before scraping
                - after_count: Article count after scraping
        """
        self.current_run["scrapers"][scraper_name] = stats
        
        # Update overall stats
        if stats.get("status") == "success":
            self.current_run["successful_scrapers"] += 1
        else:
            self.current_run["failed_scrapers"] += 1
            
        self.current_run["total_articles_scraped"] += stats.get("articles_scraped", 0)
        self.current_run["total_articles_skipped"] += stats.get("articles_skipped", 0)
        self.current_run["total_errors"] += stats.get("errors", 0)
        
    def end_run(self):
        """Mark the current run as complete and save to file"""
        self.current_run["end_time"] = datetime.now().isoformat()
        
        # Calculate duration
        if self.current_run["start_time"]:
            start = datetime.fromisoformat(self.current_run["start_time"])
            end = datetime.fromisoformat(self.current_run["end_time"])
            self.current_run["duration_seconds"] = (end - start).total_seconds()
        
        # Save to file
        self._save_to_file()
        
    def _save_to_file(self):
        """Save current run statistics to JSON file"""
        # Load existing data
        existing_data = self._load_existing_data()
        
        # Add current run to history
        if "runs" not in existing_data:
            existing_data["runs"] = []
            
        existing_data["runs"].append(self.current_run)
        
        # Update summary statistics
        existing_data["summary"] = self._calculate_summary(existing_data["runs"])
        
        # Save to file
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
            
    def _load_existing_data(self) -> Dict:
        """Load existing statistics from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
        
    def _calculate_summary(self, runs: List[Dict]) -> Dict:
        """Calculate summary statistics from all runs"""
        if not runs:
            return {}
            
        total_runs = len(runs)
        total_articles = sum(run.get("total_articles_scraped", 0) for run in runs)
        total_errors = sum(run.get("total_errors", 0) for run in runs)
        
        # Get latest run
        latest_run = runs[-1] if runs else {}
        
        # Calculate average duration
        durations = [run.get("duration_seconds", 0) for run in runs if run.get("duration_seconds")]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_runs": total_runs,
            "total_articles_scraped": total_articles,
            "total_errors": total_errors,
            "average_duration_seconds": round(avg_duration, 2),
            "latest_run_id": latest_run.get("run_id"),
            "latest_run_time": latest_run.get("start_time"),
            "latest_run_articles": latest_run.get("total_articles_scraped", 0)
        }
        
    def get_scraper_history(self, scraper_name: str, limit: int = 10) -> List[Dict]:
        """
        Get historical statistics for a specific scraper
        
        Args:
            scraper_name: Name of the scraper
            limit: Maximum number of runs to return
            
        Returns:
            List of scraper statistics from recent runs
        """
        existing_data = self._load_existing_data()
        runs = existing_data.get("runs", [])
        
        scraper_history = []
        for run in reversed(runs[-limit:]):
            if scraper_name in run.get("scrapers", {}):
                scraper_stats = run["scrapers"][scraper_name].copy()
                scraper_stats["run_id"] = run["run_id"]
                scraper_stats["run_time"] = run["start_time"]
                scraper_history.append(scraper_stats)
                
        return scraper_history
        
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        existing_data = self._load_existing_data()
        return existing_data.get("summary", {})
        
    def print_current_run_summary(self):
        """Print summary of current run"""
        print("\n" + "="*80)
        print("📊 SCRAPER RUN SUMMARY")
        print("="*80)
        print(f"Run ID: {self.current_run['run_id']}")
        print(f"Start Time: {self.current_run['start_time']}")
        print(f"End Time: {self.current_run['end_time']}")
        print(f"Duration: {self.current_run['duration_seconds']:.2f} seconds")
        print(f"Mode: {self.current_run['mode']}")
        print(f"\nScrapers: {self.current_run['successful_scrapers']}/{self.current_run['total_scrapers']} successful")
        print(f"Total Articles Scraped: {self.current_run['total_articles_scraped']}")
        print(f"Total Articles Skipped: {self.current_run['total_articles_skipped']}")
        print(f"Total Errors: {self.current_run['total_errors']}")
        print("="*80)
        
        # Print top performers
        if self.current_run["scrapers"]:
            print("\n🏆 TOP PERFORMERS:")
            sorted_scrapers = sorted(
                self.current_run["scrapers"].items(),
                key=lambda x: x[1].get("articles_scraped", 0),
                reverse=True
            )[:5]
            
            for scraper_name, stats in sorted_scrapers:
                print(f"  • {scraper_name}: {stats.get('articles_scraped', 0)} articles")
                
        print("="*80 + "\n")
