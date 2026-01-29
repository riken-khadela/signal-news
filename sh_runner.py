import subprocess
import os
import traceback
import os
import sys
import fcntl
import logging
import atexit
from logger import CustomLogger
logger = CustomLogger('/home/user1/startups/news-scrapper/logs/news_scrapper_main.log')
def run_sh_in_background():
    script_path = "/home/user1/startups/news-scrapper/run_scrapper.sh" 

    subprocess.Popen(
        ["nohup", "bash", script_path],
        stdout=open(os.devnull, 'w'),
        stderr=open(os.devnull, 'w'),
        preexec_fn=os.setpgrp  # Detach from parent
    )

    print("✅ Shell script launched in background. Python script exiting...")


LOCK_FILE = '/tmp/news_scrapper_sh.lock'
lock_file_handle = None

def acquire_lock():
    """Ensure only one instance runs at a time"""
    global lock_file_handle
    try:
        lock_file_handle = open(LOCK_FILE, 'w')
        fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
        logger.info(f"Lock acquired with PID: {os.getpid()}")
        return lock_file_handle
    except IOError:
        logger.warning("Another instance is already running. Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error acquiring lock: {e}")
        sys.exit(1)

def release_lock():
    """Release the lock file"""
    global lock_file_handle
    try:
        if lock_file_handle:
            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
            lock_file_handle.close()
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
            logger.info("Lock released successfully")
    except Exception as e:
        logger.error(f"Error releasing lock: {e}")

if __name__ == "__main__":
    # Acquire lock before starting
    acquire_lock()
    
    # Register cleanup function to release lock on exit
    atexit.register(release_lock)
    
    try:
        while True:
            run_sh_in_background()
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)