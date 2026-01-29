"""
Production-ready Selenium Bot with undetected-chromedriver
Supports headless/headed, proxies, mobile emulation, anti-detection
"""

import os
import time
import random
import json
import logging
from typing import Optional, List, Tuple, Any, Callable
from functools import wraps
from contextlib import contextmanager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    WebDriverException,
    ElementClickInterceptedException
)
import undetected_chromedriver as uc


class BotConfig:
    """Configuration for BOT instance"""
    def __init__(
        self,
        headless: bool = False,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        mobile: bool = False,
        window_size: Tuple[int, int] = (1920, 1080),
        download_dir: Optional[str] = None,
        disable_images: bool = False,
        page_load_timeout: int = 30,
        implicit_wait: int = 10,
        script_timeout: int = 30,
        enable_logging: bool = True,
        log_level: str = "INFO"
    ):
        self.headless = headless
        self.proxy = proxy
        self.user_agent = user_agent
        self.mobile = mobile
        self.window_size = window_size
        self.download_dir = download_dir
        self.disable_images = disable_images
        self.page_load_timeout = page_load_timeout
        self.implicit_wait = implicit_wait
        self.script_timeout = script_timeout
        self.enable_logging = enable_logging
        self.log_level = log_level


class BOT:
    """
    Production-ready Selenium bot with undetected-chromedriver
    
    Features:
    - Anti-detection with undetected-chromedriver
    - Headless/headed mode
    - Proxy support
    - Mobile emulation
    - Smart waits and retries
    - Cookie management
    - Screenshot on error
    - Context manager support
    
    Usage:
        with BOT(config) as bot:
            bot.go_to("https://example.com")
            bot.click((By.ID, "button"))
    """
    
    MOBILE_DEVICES = {
        "iphone_12": {
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
            "width": 390,
            "height": 844,
            "pixelRatio": 3.0
        },
        "pixel_5": {
            "userAgent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36",
            "width": 393,
            "height": 851,
            "pixelRatio": 2.75
        },
        "ipad_pro": {
            "userAgent": "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
            "width": 1024,
            "height": 1366,
            "pixelRatio": 2.0
        }
    }
    
    def __init__(self, config: Optional[BotConfig] = None):
        """Initialize bot with configuration"""
        self.config = config or BotConfig()
        self.driver = None
        self.wait = None
        self._setup_logging()
        self.setup_driver()
    
    def _setup_logging(self):
        """Setup console logging"""
        if not self.config.enable_logging:
            return
        
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_driver(self):
        """Initialize undetected Chrome driver with all options"""
        try:
            options = uc.ChromeOptions()
            
            # Headless mode
            if self.config.headless:
                options.add_argument('--headless=new')
                options.add_argument('--disable-gpu')
            
            # Window size
            options.add_argument(f'--window-size={self.config.window_size[0]},{self.config.window_size[1]}')
            
            # Proxy
            if self.config.proxy:
                options.add_argument(f'--proxy-server={self.config.proxy}')
            
            # User agent
            if self.config.user_agent:
                options.add_argument(f'--user-agent={self.config.user_agent}')
            
            # Download directory
            if self.config.download_dir:
                prefs = {
                    "download.default_directory": self.config.download_dir,
                    "download.prompt_for_download": False,
                }
                options.add_experimental_option("prefs", prefs)
            
            # Disable images for speed
            if self.config.disable_images:
                prefs = {"profile.managed_default_content_settings.images": 2}
                options.add_experimental_option("prefs", prefs)
            
            # Anti-detection settings
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            
            # Exclude automation switches
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Mobile emulation
            if self.config.mobile:
                device = self.MOBILE_DEVICES.get("iphone_12")  # Default mobile
                mobile_emulation = {
                    "deviceMetrics": {
                        "width": device["width"],
                        "height": device["height"],
                        "pixelRatio": device["pixelRatio"]
                    },
                    "userAgent": device["userAgent"]
                }
                options.add_experimental_option("mobileEmulation", mobile_emulation)
            
            # Initialize driver
            self.driver = uc.Chrome(options=options, version_main=None)
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.driver.set_script_timeout(self.config.script_timeout)
            self.driver.implicitly_wait(self.config.implicit_wait)
            
            # Initialize wait
            self.wait = WebDriverWait(self.driver, 10)
            
            # Remove webdriver flag via JavaScript
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.driver.execute_script("return navigator.userAgent").replace('Headless', '')
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            if self.config.enable_logging:
                self.logger.info("✓ Chrome driver initialized successfully")
            
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Failed to initialize driver: {e}")
            raise
    
    # ============== CONTEXT MANAGER ==============
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.quit()
    
    # ============== NAVIGATION ==============
    
    def go_to(self, url: str, retry: int = 3) -> bool:
        """Navigate to URL with retry logic"""
        for attempt in range(retry):
            try:
                self.driver.get(url)
                if self.config.enable_logging:
                    self.logger.info(f"✓ Navigated to: {url}")
                return True
            except TimeoutException:
                if self.config.enable_logging:
                    self.logger.warning(f"⚠ Timeout loading {url}, attempt {attempt + 1}/{retry}")
                if attempt == retry - 1:
                    if self.config.enable_logging:
                        self.logger.error(f"✗ Failed to load {url} after {retry} attempts")
                    return False
            except Exception as e:
                if self.config.enable_logging:
                    self.logger.error(f"✗ Error navigating to {url}: {e}")
                return False
        return False
    
    def refresh(self):
        """Refresh current page"""
        try:
            self.driver.refresh()
            if self.config.enable_logging:
                self.logger.info("✓ Page refreshed")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Error refreshing page: {e}")
    
    def back(self):
        """Go back in browser history"""
        try:
            self.driver.back()
            if self.config.enable_logging:
                self.logger.info("✓ Navigated back")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Error going back: {e}")
    
    def forward(self):
        """Go forward in browser history"""
        try:
            self.driver.forward()
            if self.config.enable_logging:
                self.logger.info("✓ Navigated forward")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Error going forward: {e}")
    
    # ============== ELEMENT FINDING ==============
    
    def find_element(self, locator: Tuple[By, str], timeout: int = 10):
        """Find element with explicit wait"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located(locator))
            return element
        except TimeoutException:
            if self.config.enable_logging:
                self.logger.error(f"✗ Element not found: {locator}")
            return None
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Error finding element {locator}: {e}")
            return None
    
    def find_elements(self, locator: Tuple[By, str], timeout: int = 10) -> List:
        """Find multiple elements with explicit wait"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located(locator))
            return elements
        except TimeoutException:
            if self.config.enable_logging:
                self.logger.warning(f"⚠ No elements found: {locator}")
            return []
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Error finding elements {locator}: {e}")
            return []
    
    def wait_for_element(self, locator: Tuple[By, str], timeout: int = 10, condition="presence"):
        """Wait for element with different conditions"""
        conditions = {
            "presence": EC.presence_of_element_located,
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable
        }
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(conditions.get(condition, EC.presence_of_element_located)(locator))
            return element
        except TimeoutException:
            if self.config.enable_logging:
                self.logger.error(f"✗ Element {condition} timeout: {locator}")
            return None
    
    def is_element_present(self, locator: Tuple[By, str], timeout: int = 5) -> bool:
        """Check if element exists without raising exception"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False
    
    # ============== INTERACTIONS ==============
    
    def click(self, locator: Tuple[By, str], timeout: int = 10, scroll: bool = True) -> bool:
        """Safe click with scroll and retry"""
        try:
            element = self.wait_for_element(locator, timeout, "clickable")
            if not element:
                return False
            
            # Scroll into view
            if scroll:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.3)
            
            # Try normal click
            try:
                element.click()
            except ElementClickInterceptedException:
                # Fallback to JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
            
            if self.config.enable_logging:
                self.logger.info(f"✓ Clicked: {locator}")
            return True
            
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Click failed on {locator}: {e}")
            return False
    
    def send_keys(self, locator: Tuple[By, str], text: str, clear: bool = True, human_like: bool = False) -> bool:
        """Send keys to element with optional human-like typing"""
        try:
            element = self.wait_for_element(locator, condition="visible")
            if not element:
                return False
            
            if clear:
                element.clear()
            
            if human_like:
                self.human_like_typing(element, text)
            else:
                element.send_keys(text)
            
            if self.config.enable_logging:
                self.logger.info(f"✓ Sent keys to: {locator}")
            return True
            
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Send keys failed on {locator}: {e}")
            return False
    
    def get_text(self, locator: Tuple[By, str], timeout: int = 10) -> Optional[str]:
        """Get element text with fallback to JavaScript"""
        try:
            element = self.find_element(locator, timeout)
            if not element:
                return None
            
            text = element.text
            if not text:
                # Fallback to textContent
                text = self.driver.execute_script("return arguments[0].textContent;", element)
            
            return text.strip() if text else None
            
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Get text failed on {locator}: {e}")
            return None
    
    def get_attribute(self, locator: Tuple[By, str], attribute: str, timeout: int = 10) -> Optional[str]:
        """Get element attribute value"""
        try:
            element = self.find_element(locator, timeout)
            if not element:
                return None
            
            return element.get_attribute(attribute)
            
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Get attribute failed on {locator}: {e}")
            return None
    
    def select_dropdown(self, locator: Tuple[By, str], value: str, by: str = "value") -> bool:
        """Select dropdown option by value, text, or index"""
        try:
            element = self.find_element(locator)
            if not element:
                return False
            
            select = Select(element)
            
            if by == "value":
                select.select_by_value(value)
            elif by == "text":
                select.select_by_visible_text(value)
            elif by == "index":
                select.select_by_index(int(value))
            
            if self.config.enable_logging:
                self.logger.info(f"✓ Selected dropdown: {locator} -> {value}")
            return True
            
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Dropdown select failed on {locator}: {e}")
            return False
    
    # ============== WINDOW/TAB/FRAME ==============
    
    def switch_to_window(self, index: int = -1):
        """Switch to window by index (-1 for last)"""
        try:
            windows = self.driver.window_handles
            self.driver.switch_to.window(windows[index])
            if self.config.enable_logging:
                self.logger.info(f"✓ Switched to window {index}")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Window switch failed: {e}")
    
    def switch_to_frame(self, locator: Tuple[By, str] = None, index: int = None):
        """Switch to iframe by locator or index"""
        try:
            if locator:
                element = self.find_element(locator)
                self.driver.switch_to.frame(element)
            elif index is not None:
                self.driver.switch_to.frame(index)
            
            if self.config.enable_logging:
                self.logger.info("✓ Switched to frame")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Frame switch failed: {e}")
    
    def switch_to_default(self):
        """Switch back to default content"""
        try:
            self.driver.switch_to.default_content()
            if self.config.enable_logging:
                self.logger.info("✓ Switched to default content")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Default content switch failed: {e}")
    
    def close_current_tab(self):
        """Close current tab and switch to last"""
        try:
            self.driver.close()
            self.switch_to_window(-1)
            if self.config.enable_logging:
                self.logger.info("✓ Closed current tab")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Close tab failed: {e}")
    
    # ============== COOKIES ==============
    
    def save_cookies(self, filepath: str):
        """Save cookies to JSON file"""
        try:
            cookies = self.driver.get_cookies()
            with open(filepath, 'w') as f:
                json.dump(cookies, f, indent=4)
            if self.config.enable_logging:
                self.logger.info(f"✓ Cookies saved to: {filepath}")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Save cookies failed: {e}")
    
    def load_cookies(self, filepath: str):
        """Load cookies from JSON file"""
        try:
            with open(filepath, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                # Remove domain if it starts with a dot
                if 'domain' in cookie and cookie['domain'].startswith('.'):
                    cookie['domain'] = cookie['domain'][1:]
                self.driver.add_cookie(cookie)
            
            if self.config.enable_logging:
                self.logger.info(f"✓ Cookies loaded from: {filepath}")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Load cookies failed: {e}")
    
    def clear_cookies(self):
        """Clear all cookies"""
        try:
            self.driver.delete_all_cookies()
            if self.config.enable_logging:
                self.logger.info("✓ Cookies cleared")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Clear cookies failed: {e}")
    
    # ============== ANTI-DETECTION ==============
    
    def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Random delay between actions"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def random_scroll(self, direction: str = "down", pixels: int = None):
        """Random scroll to mimic human behavior"""
        try:
            if pixels is None:
                pixels = random.randint(100, 500)
            
            if direction == "down":
                self.driver.execute_script(f"window.scrollBy(0, {pixels});")
            elif direction == "up":
                self.driver.execute_script(f"window.scrollBy(0, -{pixels});")
            
            time.sleep(random.uniform(0.3, 0.8))
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Random scroll failed: {e}")
    
    def human_like_typing(self, element, text: str):
        """Type text with random delays like a human"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    # ============== ERROR HANDLING ==============
    
    def take_screenshot(self, name: str = "screenshot"):
        """Take screenshot with timestamp"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            self.driver.save_screenshot(filename)
            if self.config.enable_logging:
                self.logger.info(f"✓ Screenshot saved: {filename}")
            return filename
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Screenshot failed: {e}")
            return None
    
    def save_page_source(self, name: str = "page_source"):
        """Save page HTML source"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            if self.config.enable_logging:
                self.logger.info(f"✓ Page source saved: {filename}")
            return filename
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Save page source failed: {e}")
            return None
    
    def retry(self, func: Callable, attempts: int = 3, delay: float = 1.0, *args, **kwargs) -> Any:
        """Retry a function with exponential backoff"""
        for attempt in range(attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == attempts - 1:
                    if self.config.enable_logging:
                        self.logger.error(f"✗ Retry failed after {attempts} attempts: {e}")
                    raise
                
                wait_time = delay * (2 ** attempt)
                if self.config.enable_logging:
                    self.logger.warning(f"⚠ Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
    
    # ============== UTILITIES ==============
    
    def execute_script(self, script: str, *args):
        """Execute JavaScript code"""
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Script execution failed: {e}")
            return None
    
    def get_page_source(self) -> str:
        """Get current page HTML source"""
        try:
            return self.driver.page_source
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Get page source failed: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """Get current URL"""
        try:
            return self.driver.current_url
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Get current URL failed: {e}")
            return ""
    
    def get_title(self) -> str:
        """Get page title"""
        try:
            return self.driver.title
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Get title failed: {e}")
            return ""
    
    def scroll_to_bottom(self):
        """Scroll to bottom of page"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Scroll to bottom failed: {e}")
    
    def scroll_to_top(self):
        """Scroll to top of page"""
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Scroll to top failed: {e}")
    
    # ============== CLEANUP ==============
    
    def quit(self):
        """Quit driver and cleanup"""
        try:
            if self.driver:
                self.driver.quit()
                if self.config.enable_logging:
                    self.logger.info("✓ Driver quit successfully")
        except Exception as e:
            if self.config.enable_logging:
                self.logger.error(f"✗ Quit failed: {e}")