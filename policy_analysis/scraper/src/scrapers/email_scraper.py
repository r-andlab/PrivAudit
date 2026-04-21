import re
from typing import List
from .base_scraper import BaseScraper
from src.config import Config
from src.utils import FileManager, Logger

from selenium import webdriver
from src.timeout import TimeoutHandler
from selenium import webdriver
from selenium.webdriver.common.by import By

class EmailScraper(BaseScraper):
    """Main scraper class for finding emails."""

    def __init__(self, driver: webdriver.Chrome):
        super().__init__(driver)
        self.file_manager = FileManager(scraper_type=Config.ScraperType.EMAIL)
        self.found_emails = set()

    def get_found_emails_as_list(self) -> List[str]:
        return list(self.found_emails)

    @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['email_search'], "Email search")
    def search_emails(self, website_url: str) -> List[str]:
        """Searches for emails on the webpage and saves related data."""
        EMAIL_PATTERN = r'''(?:[a-zA-Z0-9](?:[a-zA-Z0-9-._](?![.-])){0,62}[a-zA-Z0-9]|[a-zA-Z0-9])@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-](?![.-])){0,62}[a-zA-Z0-9]\.){1,3}(?:com|org|net|edu|gov|mil|co|io|us|ca|[a-zA-Z]{2,})'''

        self.found_emails.clear()
        unique_elements = set()  # Track unique HTML elements
        
        # Get subfolder paths for this URL
        # subfolder_paths = self.file_manager.get_subfolder_paths(website_url)
        
        try:
            # Get page source and find all email matches
            page_source = self.driver.page_source
            
            email_matches = re.finditer(EMAIL_PATTERN, page_source)
            
            for match in email_matches:
                email = match.group()
                
                # Find elements containing the email
                xpath = f"//*[contains(text(), '{email}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                if elements:
                    for element in elements:

                        # Get the outerHTML as a unique identifier
                        element_html = element.get_attribute('outerHTML')
                    
                        # Check if the element's HTML is unique
                        if element_html in unique_elements:
                            continue  # Skip already processed elements

                        if element.is_displayed():

                            # self.file_manager.capture_screenshots(
                            #     self.driver, element, website_url, 'email', subfolder_paths
                            # )

                            # self.file_manager.capture_html_element(
                            #     self.driver, element, website_url, 'email', subfolder_paths
                            # )
                            # Mark this element as processed
                            unique_elements.add(element_html)
                            break
                
                self.found_emails.add(email)
            
            Logger.log(f"search_emails() -> Found {len(self.found_emails)} emails on {website_url}")
            return list(self.found_emails)

        except Exception as e:
            Logger.log(f"search_emails() -> Error processing {website_url}: {str(e)}")