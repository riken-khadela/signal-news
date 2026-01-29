"""
Unified News Scraper Management System (z_main.py)
===================================================
Centralized orchestration for all news scrapers with:
- Incremental scraping (only new articles)
- Concurrent execution with thread pooling
- Comprehensive error handling and logging
- State tracking and statistics
- Cron job ready (designed for 3x daily execution)

Author: AI Assistant
Date: 2026-01-28
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import pytz
import traceback

# Import all scraper modules
import advance_materials
import azonano
import betakit
import business_insider
import canary
import cleanenergywire
import cleantechnica
import cnet
import complianceweek
import crunchbase
import fortune
import healthcareasiamagazine
import healthtechasia
import healthtechmagazine
import htn_co_uk
import intelligence360
import mining
import mobihealthnews
import neno_werk
import next_web
import phocuswire
import quantam_insider
import renewableenergyworld
import rigzone
import sacra
import tech_crunch
import tech_eu
import tech_funding
import tech_in_aisa
import wired
import worldoil
import zdnet

from logger import CustomLogger
from settings import news_details_client
from stats_tracker import StatsTracker

# Initialize timezone
ist = pytz.timezone("Asia/Kolkata")

# Configuration
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "scraper_config.json"
STATE_FILE = SCRIPT_DIR / "scraper_state.json"
LOG_DIR = SCRIPT_DIR / "log" / "z_main"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Initialize logger
logger = CustomLogger(log_folder=str(LOG_DIR))


class ScraperRegistry:
    """Registry of all available scrapers with metadata and collection mappings"""
    
    SCRAPERS = {
        "advance_materials": {
            "module": advance_materials,
            "class_name": "AdvanceMaterials",
            "collection_client": "ADVANCE_MATERIALS_MAGAZINE_client",
            "collection_name": "ADVANCE_MATERIALS_MAGAZINE",
            "priority": 1,
            "type": "pagination"
        },
        "azonano": {
            "module": azonano,
            "class_name": "Azonano",
            "collection_client": "AZONANO_client",
            "collection_name": "AZONANO",
            "priority": 1,
            "type": "pagination"
        },
        "betakit": {
            "module": betakit,
            "class_name": "BetaKit",
            "collection_client": "BETA_KIT_client",
            "collection_name": "BETA_KIT",
            "priority": 1,
            "type": "pagination"
        },
        "business_insider": {
            "module": business_insider,
            "class_name": "BusinessInsider",
            "collection_client": "BUSINESSINSIDER_client",
            "collection_name": "BUSINESSINSIDER",
            "priority": 2,
            "type": "api"
        },
        "canary": {
            "module": canary,
            "class_name": "Canary",
            "collection_client": "CANARY_client",
            "collection_name": "CANARY",
            "priority": 1,
            "type": "pagination"
        },
        "cleanenergywire": {
            "module": cleanenergywire,
            "class_name": "CleanEnergyWire",
            "collection_client": "CLEANENERGY_WIRE_client",
            "collection_name": "CLEANENERGY_WIRE",
            "priority": 1,
            "type": "pagination"
        },
        "cleantechnica": {
            "module": cleantechnica,
            "class_name": "CleanTechChina",
            "collection_client": "CLEANTECHCHINA_client",
            "collection_name": "CLEANTECHCHINA",
            "priority": 1,
            "type": "pagination"
        },
        "cnet": {
            "module": cnet,
            "class_name": "Cnet",
            "collection_client": "CNET_client",
            "collection_name": "CNET",
            "priority": 1,
            "type": "api"
        },
        "complianceweek": {
            "module": complianceweek,
            "class_name": "ComplianceWeek",
            "collection_client": "COMPLIANCEWEEK_client",
            "collection_name": "COMPLIANCEWEEK",
            "priority": 1,
            "type": "pagination"
        },
        "crunchbase": {
            "module": crunchbase,
            "class_name": "CrunchBase",
            "collection_client": "CRUNCHBASE_client",
            "collection_name": "CRUNCHBASE",
            "priority": 1,
            "type": "pagination"
        },
        "fortune": {
            "module": fortune,
            "class_name": "Fortune",
            "collection_client": "FORTUNE_client",
            "collection_name": "FORTUNE",
            "priority": 1,
            "type": "pagination"
        },
        "healthcareasiamagazine": {
            "module": healthcareasiamagazine,
            "class_name": "HealthCareAsiaMagazine",
            "collection_client": "HEALTHCAREASIAMAGAZINE_client",
            "collection_name": "HEALTHCAREASIAMAGAZINE",
            "priority": 1,
            "type": "pagination"
        },
        "healthtechasia": {
            "module": healthtechasia,
            "class_name": "HealthTechAsia",
            "collection_client": "HEALTHTECHASIA_client",
            "collection_name": "HEALTHTECHASIA",
            "priority": 1,
            "type": "pagination"
        },
        "healthtechmagazine": {
            "module": healthtechmagazine,
            "class_name": "HealthTechMagazine",
            "collection_client": "HEALTHTECHMAGAZINE_client",
            "collection_name": "HEALTHTECHMAGAZINE",
            "priority": 1,
            "type": "api"
        },
        "htn_co_uk": {
            "module": htn_co_uk,
            "class_name": "HTN_CO_UK",
            "collection_client": "HTN_CO_UK_client",
            "collection_name": "HTN_CO_UK",
            "priority": 1,
            "type": "pagination"
        },
        "intelligence360": {
            "module": intelligence360,
            "class_name": "Inteligence360",
            "collection_client": "intelligence360_client",
            "collection_name": "intelligence360",
            "priority": 1,
            "type": "pagination"
        },
        "mining": {
            "module": mining,
            "class_name": "Mining",
            "collection_client": "MINING_client",
            "collection_name": "MINING",
            "priority": 1,
            "type": "pagination"
        },
        "mobihealthnews": {
            "module": mobihealthnews,
            "class_name": "MobileHealthNews",
            "collection_client": "MobileHealthNews_client",
            "collection_name": "MobileHealthNews",
            "priority": 1,
            "type": "pagination"
        },
        "neno_werk": {
            "module": neno_werk,
            "class_name": "NanoWerk",
            "collection_client": "NANOWERK_client",
            "collection_name": "NANOWERK",
            "priority": 1,
            "type": "pagination"
        },
        "next_web": {
            "module": next_web,
            "class_name": "NextWeb",
            "collection_client": "TEST_NEXT_WEB_client",
            "collection_name": "TEST_NEXT_WEB",
            "priority": 1,
            "type": "pagination"
        },
        "phocuswire": {
            "module": phocuswire,
            "class_name": "PhocusWire",
            "collection_client": "PHOCUSWIRE_client",
            "collection_name": "PHOCUSWIRE",
            "priority": 1,
            "type": "pagination"
        },
        "quantam_insider": {
            "module": quantam_insider,
            "class_name": "QuantamInsider",
            "collection_client": "THE_QUANTUM_INSIDER_client",
            "collection_name": "THE_QUANTUM_INSIDER",
            "priority": 1,
            "type": "pagination"
        },
        "renewableenergyworld": {
            "module": renewableenergyworld,
            "class_name": "ReNewableEnergyWorld",
            "collection_client": "ReNewableEnergyWorld_client",
            "collection_name": "RENEWABLEENERGYWORLD",
            "priority": 1,
            "type": "pagination"
        },
        "rigzone": {
            "module": rigzone,
            "class_name": "RigZone",
            "collection_client": "RIGZONE_client",
            "collection_name": "RIGZONE",
            "priority": 1,
            "type": "pagination"
        },
        "sacra": {
            "module": sacra,
            "class_name": "Sacra",
            "collection_client": "SACRA_client",
            "collection_name": "SACRA",
            "priority": 3,
            "type": "selenium"
        },
        "tech_crunch": {
            "module": tech_crunch,
            "class_name": "TechCrunch",
            "collection_client": "news_details_client",
            "collection_name": "news_details",
            "priority": 1,
            "type": "pagination"
        },
        "tech_eu": {
            "module": tech_eu,
            "class_name": "TechEu",
            "collection_client": "TECH_EU_client",
            "collection_name": "TECH_EU",
            "priority": 1,
            "type": "pagination"
        },
        "tech_funding": {
            "module": tech_funding,
            "class_name": "TechFunding",
            "collection_client": "news_details_client",
            "collection_name": "news_details",
            "priority": 1,
            "type": "pagination"
        },
        "tech_in_aisa": {
            "module": tech_in_aisa,
            "class_name": "TechInAsia",
            "collection_client": "TECHINASIA_client",
            "collection_name": "TECHINASIA",
            "priority": 3,
            "type": "selenium"
        },
        "wired": {
            "module": wired,
            "class_name": "Wired",
            "collection_client": "THE_WIRED_client",
            "collection_name": "THE_WIRED",
            "priority": 1,
            "type": "pagination"
        },
        "worldoil": {
            "module": worldoil,
            "class_name": "WorldOil",
            "collection_client": "WORLDOIL_client",
            "collection_name": "WORLDOIL",
            "priority": 1,
            "type": "pagination"
        },
        "zdnet": {
            "module": zdnet,
            "class_name": "Zdnet",
            "collection_client": "ZDNET_client",
            "collection_name": "ZDNET",
            "priority": 1,
            "type": "pagination"
        },
    }


class ScraperConfig:
    """Configuration manager for scraper settings"""
    
    DEFAULT_CONFIG = {
        "mode": "incremental",  # "full" or "incremental"
        "max_workers": 6,
        "max_pages_per_scraper": 5,  # For incremental mode
        "skip_existing": True,  # Skip articles already in DB
        "skip_threshold": 10,  # Stop after N consecutive skips
        "enable_skip_logic": True,  # Enable early termination on skips
        "retry_failed": True,
        "timeout_per_scraper": 3600,  # 1 hour max per scraper
        "enabled_scrapers": "all",  # "all" or list of scraper names
        "disabled_scrapers": [],  # List of scrapers to disable
        "auto_merge": False,  # Auto-run merged_news.py after scraping
        "merge_date_filter": "2025-01-01",  # Date filter for merging
    }
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded_config)
                logger.info(f"✅ Loaded configuration from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"❌ Error loading config: {e}. Using defaults.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self.save_config(self.DEFAULT_CONFIG)
            logger.info(f"📝 Created default configuration at {self.config_file}")
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"💾 Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
    
    def is_scraper_enabled(self, scraper_name: str) -> bool:
        """Check if a scraper is enabled"""
        if scraper_name in self.config.get("disabled_scrapers", []):
            return False
        
        enabled = self.config.get("enabled_scrapers", "all")
        if enabled == "all":
            return True
        return scraper_name in enabled


class ScraperState:
    """State tracker for scraper execution history"""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state = self.load_state()
    
    def load_state(self) -> Dict:
        """Load state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ Error loading state: {e}")
                return {}
        return {}
    
    def save_state(self):
        """Save state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving state: {e}")
    
    def get_last_run(self, scraper_name: str) -> Optional[str]:
        """Get last successful run timestamp for a scraper"""
        return self.state.get(scraper_name, {}).get("last_success")
    
    def update_scraper_state(self, scraper_name: str, success: bool, 
                            articles_collected: int = 0, error: str = None):
        """Update state for a scraper"""
        now = datetime.now(ist).isoformat()
        
        if scraper_name not in self.state:
            self.state[scraper_name] = {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "total_articles": 0
            }
        
        self.state[scraper_name]["total_runs"] += 1
        self.state[scraper_name]["last_run"] = now
        
        if success:
            self.state[scraper_name]["successful_runs"] += 1
            self.state[scraper_name]["last_success"] = now
            self.state[scraper_name]["total_articles"] += articles_collected
            self.state[scraper_name]["last_articles_count"] = articles_collected
            if "last_error" in self.state[scraper_name]:
                del self.state[scraper_name]["last_error"]
        else:
            self.state[scraper_name]["failed_runs"] += 1
            self.state[scraper_name]["last_error"] = error
            self.state[scraper_name]["last_error_time"] = now
        
        self.save_state()


class UnifiedScraperManager:
    """Main orchestrator for all news scrapers"""
    
    def __init__(self):
        self.config = ScraperConfig(CONFIG_FILE)
        self.state = ScraperState(STATE_FILE)
        self.registry = ScraperRegistry()
        self.stats_tracker = StatsTracker(str(SCRIPT_DIR / "scraper_stats.json"))
        self.stats = {
            "total_scrapers": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_articles": 0,
            "start_time": None,
            "end_time": None
        }
    
    def run_scraper(self, scraper_name: str, scraper_info: Dict) -> Dict:
        """Execute a single scraper"""
        result = {
            "scraper": scraper_name,
            "success": False,
            "articles_collected": 0,
            "articles_skipped": 0,
            "errors": 0,
            "error": None,
            "duration": 0,
            "before_count": 0,
            "after_count": 0
        }
        
        start_time = time.time()
        scraper_start_time = datetime.now(ist).isoformat()
        
        try:
            logger.info(f"🚀 Starting scraper: {scraper_name}")
            
            # Get the scraper class
            module = scraper_info["module"]
            class_name = scraper_info["class_name"]
            scraper_class = getattr(module, class_name)
            
            # Get the correct collection for this scraper
            import settings
            collection_client_name = scraper_info.get("collection_client", "news_details_client")
            collection_client = getattr(settings, collection_client_name)
            
            # Instantiate and run
            scraper_instance = scraper_class()
            
            # Pass configuration to scraper if it supports it
            if hasattr(scraper_instance, 'set_config'):
                scraper_instance.set_config({
                    'max_pages': self.config.config.get('max_pages_per_scraper', 5),
                    'skip_threshold': self.config.config.get('skip_threshold', 10),
                    'enable_skip_logic': self.config.config.get('enable_skip_logic', True),
                    'mode': self.config.config.get('mode', 'incremental')
                })
            
            # Get article count before
            before_count = collection_client.count_documents({})
            result["before_count"] = before_count
            
            # Run the scraper
            scraper_instance.run()
            
            # Get article count after
            after_count = collection_client.count_documents({})
            result["after_count"] = after_count
            articles_collected = after_count - before_count
            
            # Get scraper statistics if available
            if hasattr(scraper_instance, 'consecutive_skips'):
                result["articles_skipped"] = scraper_instance.consecutive_skips
            if hasattr(scraper_instance, 'stats'):
                result["errors"] = scraper_instance.stats.get('errors', 0)
            
            result["success"] = True
            result["articles_collected"] = articles_collected
            
            logger.info(f"✅ {scraper_name} completed successfully. Articles: {articles_collected}")
            
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            result["error"] = error_msg
            logger.error(f"❌ {scraper_name} failed: {str(e)}")
            logger.error(traceback.format_exc())
        
        finally:
            result["duration"] = time.time() - start_time
            scraper_end_time = datetime.now(ist).isoformat()
            
            # Update state
            self.state.update_scraper_state(
                scraper_name,
                result["success"],
                result["articles_collected"],
                result["error"]
            )
            
            # Add to stats tracker
            self.stats_tracker.add_scraper_stats(scraper_name, {
                "status": "success" if result["success"] else "failed",
                "start_time": scraper_start_time,
                "end_time": scraper_end_time,
                "duration_seconds": result["duration"],
                "articles_scraped": result["articles_collected"],
                "articles_skipped": result.get("articles_skipped", 0),
                "errors": result.get("errors", 0),
                "collection": scraper_info.get("collection_name", "unknown"),
                "before_count": result.get("before_count", 0),
                "after_count": result.get("after_count", 0),
                "error_message": result.get("error", "")[:200] if result.get("error") else ""
            })
        
        return result
    
    def get_enabled_scrapers(self) -> List[tuple]:
        """Get list of enabled scrapers sorted by priority"""
        enabled = []
        
        for name, info in self.registry.SCRAPERS.items():
            if self.config.is_scraper_enabled(name):
                enabled.append((name, info))
        
        # Sort by priority (lower number = higher priority)
        enabled.sort(key=lambda x: x[1]["priority"])
        
        return enabled
    
    def run_all_scrapers(self):
        """Execute all enabled scrapers with thread pool"""
        self.stats["start_time"] = datetime.now(ist)
        
        enabled_scrapers = self.get_enabled_scrapers()
        self.stats["total_scrapers"] = len(enabled_scrapers)
        
        # Start stats tracking
        self.stats_tracker.start_run(
            mode=self.config.config['mode'],
            total_scrapers=len(enabled_scrapers)
        )
        
        logger.info("=" * 80)
        logger.info("🎯 UNIFIED NEWS SCRAPER SYSTEM - STARTING")
        logger.info(f"⏰ Start Time: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"⚙️  Mode: {self.config.config['mode']}")
        logger.info(f"👥 Max Workers: {self.config.config['max_workers']}")
        logger.info("=" * 80)
        
        logger.info(f"📋 Enabled Scrapers: {len(enabled_scrapers)}")
        
        if not enabled_scrapers:
            logger.warning("⚠️  No scrapers enabled. Exiting.")
            return
        
        # Execute scrapers concurrently
        max_workers = self.config.config["max_workers"]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_scraper = {
                executor.submit(self.run_scraper, name, info): name
                for name, info in enabled_scrapers
            }
            
            for future in as_completed(future_to_scraper):
                scraper_name = future_to_scraper[future]
                try:
                    result = future.result()
                    
                    if result["success"]:
                        self.stats["successful"] += 1
                        self.stats["total_articles"] += result["articles_collected"]
                    else:
                        self.stats["failed"] += 1
                    
                    logger.info(
                        f"📊 Progress: {self.stats['successful'] + self.stats['failed']}/{self.stats['total_scrapers']} "
                        f"(✅ {self.stats['successful']} | ❌ {self.stats['failed']})"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Unexpected error with {scraper_name}: {e}")
                    self.stats["failed"] += 1
        
        self.stats["end_time"] = datetime.now(ist)
        
        # End stats tracking and save to file
        self.stats_tracker.end_run()
        
        self.print_summary()
        
        # Print stats summary
        self.stats_tracker.print_current_run_summary()
    
    def print_summary(self):
        """Print execution summary"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info("=" * 80)
        logger.info("📈 EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        logger.info(f"📊 Total Scrapers: {self.stats['total_scrapers']}")
        logger.info(f"✅ Successful: {self.stats['successful']}")
        logger.info(f"❌ Failed: {self.stats['failed']}")
        logger.info(f"📰 Total Articles Collected: {self.stats['total_articles']}")
        logger.info(f"⏰ End Time: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("=" * 80)
        
        # Print failed scrapers if any
        if self.stats["failed"] > 0:
            logger.warning("⚠️  Failed Scrapers:")
            for name, state in self.state.state.items():
                if "last_error" in state:
                    logger.warning(f"  - {name}: {state.get('last_error', 'Unknown error')[:100]}")


def main():
    """Main entry point"""
    try:
        manager = UnifiedScraperManager()
        manager.run_all_scrapers()
    except KeyboardInterrupt:
        logger.warning("⚠️  Interrupted by user. Exiting gracefully...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
