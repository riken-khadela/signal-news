import os
import datetime
import pytz

tz = pytz.timezone('Asia/Kolkata')

class CustomLogger:
    def __init__(self, log_folder: str):
        if not log_folder:
            raise ValueError("❌ Please provide a valid log folder path.")

        self.log_folder = os.path.abspath(log_folder)
        self._setup_log_directory()
        print(f"Log file location : {os.getcwd()}/{self.log_folder}")
        
        
        
        # Define log file paths
        self.files = {
            "info": os.path.join(self.log_folder, "info.log"),
            "error": os.path.join(self.log_folder, "error.log"),
            "warning": os.path.join(self.log_folder, "warning.log"),
            "log": os.path.join(self.log_folder, "general.log"),
        }
        # Create log files if they don't exist
        for file in self.files.values():
            if not os.path.exists(file):
                open(file, 'a').close()

    def _setup_log_directory(self):
        """Ensure that the directory for logs exists."""
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)
            print(f"📁 Created log directory: {self.log_folder}")

    def _write_log(self, level: str, message: str):
        """Internal method to write a log entry to the correct file."""
        timestamp = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"{timestamp} - {level.upper()} - {message}\n"

        print(log_message.strip())
        
        # Write to general log
        with open(self.files["log"], "a", encoding="utf-8") as f:
            f.write(log_message)

        # Write to specific log file
        level_file = self.files.get(level.lower())
        if level_file:
            with open(level_file, "a", encoding="utf-8") as f:
                f.write(log_message)

    def info(self, message: str):
        self._write_log("info", message)

    def error(self, message: str):
        self._write_log("error", message)

    def warning(self, message: str):
        self._write_log("warning", message)

    def log(self, message: str):
        self._write_log("info", message)
