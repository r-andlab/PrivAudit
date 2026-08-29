# Page loader
import time
from src.scrapers import BaseScraper
from src.config import Config
from src.utils import FileManager, Logger

from selenium import webdriver
from src.timeout import TimeoutHandler
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

class PageLoader(BaseScraper):

    def __init__(self, driver: webdriver.Chrome):
        super().__init__(driver)

    def load_url(self, website_url: str) -> bool:
        try:
            self.driver.get(website_url)
            Logger.log(f"PageLoader.load_url() -> Successfully fetched website: {website_url}")
            return True
        except Exception as e:
            Logger.log(f"PageLoader.load_url() -> Failed to fetch website {website_url}: {str(e)}")
            return False

    def save_page_source(self, website_url: str) -> bool:
        page_source = self.driver.page_source
        if page_source:
            FileManager.capture_page_source(page_source, website_url)
        else:
            Logger.log(f"Failed to capture page source website {website_url}")

    @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['page_load'], "Page load")
    def attempt_page_load(self) -> bool:
        Logger.log(f"PageLoader.attempt_page_load() -> Waiting for Page to load with timeout set at - {Config.TIMEOUT_SECONDS['page_load']}s")
        try:
            WebDriverWait(self.driver, Config.TIMEOUT_SECONDS['page_load']).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            Logger.log("PageLoader.attempt_page_load() -> Page has finished loading.")
            return True
        except Exception as e:
            Logger.log(f"PageLoader.attempt_page_load() -> Page load timeout: {str(e)}")
            return False

    @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['scroll'], "Page scroll")
    def attempt_scroll(self, pause_time: int = 2) -> bool:
        Logger.log(f"PageLoader.attempt_scroll() -> Scrolling through the page with timeout set at - {Config.TIMEOUT_SECONDS['scroll']}s")
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause_time)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            Logger.log("PageLoader.attempt_scroll() -> Page scrolling completed successfully.")
            return True
        except Exception as e:
            Logger.log(f"PageLoader.attempt_scroll() -> Error during scrolling: {str(e)}")
            return False
