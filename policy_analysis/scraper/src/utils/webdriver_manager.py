from src.config import Config
from src.utils import Logger

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver

class WebDriverManager:
    """Manages Selenium WebDriver configuration and operations."""

    @staticmethod
    def create_driver() -> webdriver.Chrome:
        """Creates and configures a Chrome WebDriver instance."""
        Logger.log("Initializing Chrome WebDriver...")
        options = Options()
        # chrome_options.add_argument("--headless")
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.page_load_strategy = "none"
        
        driver = webdriver.Chrome(service=Service(), options=options)
        driver.set_script_timeout(Config.TIMEOUT_SECONDS['total_search'])
        Logger.log("Chrome WebDriver initialized successfully.")
        return driver