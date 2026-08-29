# Use a set to store unique phone numbers
import re
from typing import List
from .base_scraper import BaseScraper
from src.config import Config
from src.utils import FileManager, Logger

from selenium import webdriver
from src.timeout import TimeoutHandler
from selenium import webdriver
from selenium.webdriver.common.by import By

class PhoneScraper(BaseScraper):

    def __init__(self, driver: webdriver.Chrome):
        super().__init__(driver)
        self.file_manager = FileManager(scraper_type=Config.ScraperType.PHONE)
        self.found_numbers = set()

    def get_found_numbers_as_list(self) -> List[str]:
        return list(self.found_numbers)

    @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['phone_search'], "Phone number search")
    def search_phone_numbers(self, website_url: str) -> List[str]:

        PHONE_PATTERN = r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4})"
        self.found_numbers.clear()
        unique_elements = set()

        try:

            target_tags = ['a', 'span', 'div', 'p', 'li']

            for tag in target_tags:
                elements = self.driver.find_elements(By.TAG_NAME, tag)

                for element in elements:

                    element_html = element.get_attribute('outerHTML')

                    if element_html in unique_elements:
                        continue

                    text_content = element.text
                    href = element.get_attribute('href')

                    if href and href.startswith("tel:"):
                        phone_number = href.split("tel:")[1]
                        self.found_numbers.add(phone_number)

                    phone_matches = re.finditer(PHONE_PATTERN, text_content)
                    for match in phone_matches:
                        phone_number = match.group()

                        if '.' in phone_number:
                            continue
                        digits_only = re.sub(r'\D', '', phone_number)
                        if not (7 <= len(digits_only) <= 15):
                            continue

                        if element.is_displayed():

                            unique_elements.add(element_html)

                        self.found_numbers.add(phone_number)

            Logger.log(f"search_phone_numbers() -> Found {len(self.found_numbers)} phone numbers on {website_url}")
            return list(self.found_numbers)

        except Exception as e:
            Logger.log(f"search_phone_numbers() -> Error processing {website_url}: {str(e)}")
