# Cron Job Setup Guide - Linux

## Quick Setup Commands

### 1. Edit Crontab
```bash
crontab -e
```

### 2. Add Cron Job Entry

**Run 3 times daily (8 AM, 2 PM, 8 PM IST):**
```cron
0 8,14,20 * * * cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py >> /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log 2>&1
```

**Replace the path with your actual path:**
```cron
0 8,14,20 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

### 3. Save and Exit
- **vim/vi:** Press `ESC`, then type `:wq` and press `ENTER`
- **nano:** Press `CTRL+X`, then `Y`, then `ENTER`

## Cron Schedule Examples

### Every 8 hours (3 times daily)
```cron
0 */8 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

### Specific times (8 AM, 2 PM, 8 PM)
```cron
0 8,14,20 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

### Every 6 hours
```cron
0 */6 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

### Every 4 hours
```cron
0 */4 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

### Once daily at 9 AM
```cron
0 9 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

### Twice daily (9 AM and 9 PM)
```cron
0 9,21 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

## Cron Syntax Explained

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday=0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

## Step-by-Step Setup

### Step 1: Find Python Path
```bash
which python3
# Output: /usr/bin/python3
```

### Step 2: Find Your Project Path
```bash
pwd
# Example: /home/riken/news-scrapper/news-scrapper/past_data_server
```

### Step 3: Create Log Directory (if needed)
```bash
mkdir -p /home/riken/news-scrapper/news-scrapper/past_data/Logs
```

### Step 4: Test the Command Manually
```bash
cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py
```

### Step 5: Add to Crontab
```bash
crontab -e
```

Add this line (adjust paths):
```cron
0 8,14,20 * * * cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py >> /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log 2>&1
```

### Step 6: Verify Crontab
```bash
crontab -l
```

## Complete Cron Entry Breakdown

```cron
0 8,14,20 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py >> /path/to/logs/cron.log 2>&1
```

**Explanation:**
- `0 8,14,20 * * *` - Run at minute 0 of hours 8, 14, and 20 (8 AM, 2 PM, 8 PM)
- `cd /path/to/past_data_server` - Change to project directory
- `&&` - Execute next command only if cd succeeds
- `/usr/bin/python3 z_main.py` - Run the scraper with full Python path
- `>>` - Append output to log file
- `/path/to/logs/cron.log` - Log file location
- `2>&1` - Redirect errors to same log file

## Environment Variables (if needed)

If your script needs environment variables, create a wrapper script:

**create_wrapper.sh:**
```bash
#!/bin/bash
# Save as: /home/riken/news-scrapper/run_scraper.sh

# Set environment variables
export PATH=/usr/local/bin:/usr/bin:/bin
export PYTHONPATH=/home/riken/news-scrapper/news-scrapper/past_data_server

# Change to project directory
cd /home/riken/news-scrapper/news-scrapper/past_data_server

# Activate virtual environment (if using one)
# source /path/to/venv/bin/activate

# Run the scraper
/usr/bin/python3 z_main.py

# Exit with the script's exit code
exit $?
```

**Make it executable:**
```bash
chmod +x /home/riken/news-scrapper/run_scraper.sh
```

**Cron entry using wrapper:**
```cron
0 8,14,20 * * * /home/riken/news-scrapper/run_scraper.sh >> /home/riken/news-scrapper/logs/cron.log 2>&1
```

## Monitoring and Debugging

### View Cron Log
```bash
tail -f /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log
```

### View System Cron Log
```bash
# Ubuntu/Debian
grep CRON /var/log/syslog

# CentOS/RHEL
grep CRON /var/log/cron
```

### Check if Cron is Running
```bash
systemctl status cron
# or
service cron status
```

### Test Cron Job Manually
```bash
# Run the exact command from crontab
cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py >> /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log 2>&1
```

### View Recent Cron Executions
```bash
# Last 20 lines of cron log
tail -20 /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log

# Watch log in real-time
tail -f /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log
```

## Common Issues and Solutions

### Issue 1: Cron job doesn't run
**Solution:** Check cron service
```bash
sudo systemctl status cron
sudo systemctl start cron
```

### Issue 2: Script runs manually but not via cron
**Solution:** Use absolute paths for everything
```cron
# Bad (relative paths)
0 8 * * * cd past_data_server && python3 z_main.py

# Good (absolute paths)
0 8 * * * cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py
```

### Issue 3: Environment variables not available
**Solution:** Use wrapper script (see above) or set in crontab
```cron
PATH=/usr/local/bin:/usr/bin:/bin
PYTHONPATH=/home/riken/news-scrapper/news-scrapper/past_data_server

0 8,14,20 * * * cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py >> /home/riken/news-scrapper/logs/cron.log 2>&1
```

### Issue 4: Permission denied
**Solution:** Check file permissions
```bash
chmod +x /home/riken/news-scrapper/news-scrapper/past_data_server/z_main.py
chmod +w /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log
```

## Email Notifications (Optional)

### Enable Email Notifications
Add to top of crontab:
```cron
MAILTO=your-email@example.com

0 8,14,20 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py
```

### Disable Email Notifications
```cron
MAILTO=""

0 8,14,20 * * * cd /path/to/past_data_server && /usr/bin/python3 z_main.py
```

## Recommended Setup

**For production (3 times daily):**
```cron
# Run at 8 AM, 2 PM, and 8 PM IST
0 8,14,20 * * * cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py >> /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log 2>&1
```

## Useful Cron Commands

```bash
# Edit crontab
crontab -e

# List current crontab
crontab -l

# Remove all cron jobs
crontab -r

# Edit crontab for specific user (as root)
sudo crontab -u username -e

# List crontab for specific user (as root)
sudo crontab -u username -l
```

## Log Rotation (Optional)

To prevent log files from growing too large, set up log rotation:

**Create /etc/logrotate.d/news-scraper:**
```bash
/home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

## Quick Copy-Paste Command

**Replace `/home/riken/news-scrapper/news-scrapper/past_data_server` with your actual path:**

```bash
# Open crontab editor
crontab -e

# Add this line (adjust path):
0 8,14,20 * * * cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py >> /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log 2>&1
```

## Verify Setup

After adding the cron job:

```bash
# 1. List crontab to verify
crontab -l

# 2. Check cron service
systemctl status cron

# 3. Wait for next scheduled run or test manually
cd /home/riken/news-scrapper/news-scrapper/past_data_server && /usr/bin/python3 z_main.py

# 4. Monitor the log
tail -f /home/riken/news-scrapper/news-scrapper/past_data/Logs/cron.log
```

---

**Ready to use!** Just replace the paths with your actual paths and run `crontab -e` to add the job.
