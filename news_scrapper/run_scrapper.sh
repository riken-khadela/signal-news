# Activate the virtual environment
source /home/riken/news-scrapper/news-scrapper/env/bin/python
pkill -f python
# Navigate to the script directory
cd /home/riken/news-scrapper/news-scrapper

# Create log directory if it doesn't exist
mkdir -p log
log_file="log/main.log"
pwd
# Run the scraper
/home/riken/news-scrapper/news-scrapper/env/bin/python main.py >> log/main.log
