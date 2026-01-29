#!/bin/bash

# Configuration
SCRIPT_DIR="/home/riken/news-scrapper/news-scrapper"
VENV_PATH="$SCRIPT_DIR/env"
PYTHON_SCRIPT="main.py"
LOG_DIR="$SCRIPT_DIR/log"
LOG_FILE="$LOG_DIR/main.log"
TIMEOUT=300  # 5 minutes in seconds

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Change to script directory
cd "$SCRIPT_DIR" || exit 1

# Log start time
echo "$(date): Starting news scrapper" >> "$LOG_FILE"

# Run the Python script with 5-minute timeout
timeout $TIMEOUT "$VENV_PATH/bin/python" "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

# Check if timeout occurred
if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date): Script timed out after 5 minutes" >> "$LOG_FILE"
else
    echo "$(date): Script completed with exit code: $EXIT_CODE" >> "$LOG_FILE"
fi

exit $EXIT_CODE