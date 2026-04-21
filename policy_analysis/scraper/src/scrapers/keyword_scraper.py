from typing import Dict, Set
from .base_scraper import BaseScraper
from src.config import Config
from src.utils import FileManager, Logger

from selenium import webdriver
from src.timeout import TimeoutHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

class KeywordScraper(BaseScraper):
    """Main scraper class for finding keywords across categories."""

    def __init__(self, driver: webdriver.Chrome):
        super().__init__(driver)
        self.file_manager = FileManager(scraper_type=Config.ScraperType.KEYWORD)
        self.keyword_counts = {}
        self.categories = {
            "Generic": ["submit a request", "Submit a Request", "United States Regional Privacy Notice", "CCPA"],
            "Right_To_Delete": ["Request Deletion", "Rights to Delete", "Request to Delete",
                              "Right of Deletion", "Right to Delete", "Delete My Data",
                              "Deletion", "Erase", "Erasure", "Deleting", "Delete",
                              "Right to Deletion", "Deletion", "Right to Request Deletion"],
            "Right_To_Know": ["Access", "Copy and Right to Know", "Right to Know", "Right to Know and Access",
                            "Request to Know", "Rights to Know", "Download Your Data", "Export",
                            "Request Access", "Request to Access", "Portability", "Right to Portability",
                            "Right to Access"],
            "Right_To_Correct": ["Request Corrections", "Request Correction", "Rectify", "Correction", "Rectification", "Right to Correct",
                               "Request to correct", "Right to Correction", "Correct", "Right to Request Correction"],
            "Opt_Out": ["Opt Out", "Right to opt-out", "Opt-out", "Right to Opt Out of Targeted Advertising"],
            "Right_To_Limit": ["Restrict", "Right to Restrict", "Right to Limit Use"],
            "Agents": ["Designated Agent", "Authorized Agent", "Authorized Agents", "Designated Agents"],
            "Discrimination": ["Non-Discrimination", "Right to Equal Service", "Right to Non-Discrimination"]
        }

    def is_element_descendant(self, element: WebElement, processed_elements: Set[WebElement]) -> bool:
        """Check if the element is a descendant of any already processed element."""
        try:
            for processed in processed_elements:
                try:
                    # Check if any processed element contains the current element
                    is_descendant = self.driver.execute_script("""
                        return arguments[0].contains(arguments[1]);
                    """, processed, element)
                    if is_descendant:
                        return True
                except StaleElementReferenceException:
                    continue
            return False
        except Exception:
            return False

    @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['keyword_search'], "Keyword search")
    def search_keywords(self, website_url: str) -> Dict[str, Dict[str, int]]:
        """Searches for keywords in specific HTML tags and saves related data."""
        self.keyword_counts = {}
        processed_elements = set()  # Track processed WebElements
        
        # Get subfolder paths for this URL
        # subfolder_paths = self.file_manager.get_subfolder_paths(website_url)
        
        try:
            # Define tags to check for keywords
            target_tags = ['a', 'span', 'div', 'p', 'li', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            
            for tag in target_tags:
                elements = self.driver.find_elements(By.TAG_NAME, tag)
                
                for element in elements:
                    try:
                        # Skip if element is stale
                        if not element.is_enabled():
                            continue
                            
                        # Skip if element is descendant of already processed element
                        if self.is_element_descendant(element, processed_elements):
                            continue
                        
                        # Extract text content
                        text_content = element.text.strip()
                        
                        if not text_content:
                            continue
                        
                        # Track if this element contained any keywords
                        found_keyword = False
                        
                        # Search for keywords in each category
                        for category, keywords in self.categories.items():
                            category_found = False  # Track if category needs to be added
                            
                            for keyword in keywords:
                                # Case-insensitive search
                                count = text_content.lower().count(keyword.lower())
                                
                                if count > 0:
                                    found_keyword = True
                                    category_found = True
                                    
                                    # Initialize category if not exists
                                    if category not in self.keyword_counts:
                                        self.keyword_counts[category] = {}
                                    
                                    # Add or update keyword count
                                    if keyword not in self.keyword_counts[category]:
                                        self.keyword_counts[category][keyword] = count
                                    else:
                                        self.keyword_counts[category][keyword] += count
                                    
                                    # Capture screenshots and HTML only if element is visible
                                    # if element.is_displayed():
                                    #     self.file_manager.capture_screenshots(
                                    #         self.driver, element, website_url, f'keyword_{category}', subfolder_paths
                                    #     )
                                        
                                    #     self.file_manager.capture_html_element(
                                    #         self.driver, element, website_url, f'keyword_{category}', subfolder_paths
                                    #     )
                        
                        # Only add to processed elements if we found a keyword
                        if found_keyword:
                            processed_elements.add(element)
                        
                    except StaleElementReferenceException:
                        continue
            
            # Remove empty categories
            self.keyword_counts = {
                category: keyword_dict 
                for category, keyword_dict in self.keyword_counts.items() 
                if keyword_dict
            }
            
            Logger.log(f"search_keywords() -> Found keywords in {len(self.keyword_counts)} categories on {website_url}")
            return self.keyword_counts

        except Exception as e:
            Logger.log(f"search_keywords() -> Error processing {website_url}: {str(e)}")
            return {}