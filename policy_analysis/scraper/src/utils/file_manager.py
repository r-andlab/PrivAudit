import os
import re
import time
import shutil
import uuid
from typing import Dict, Any
from datetime import datetime
from src.config import Config
from .logger import Logger
# Third-party imports
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

class FileManager:
    """Generic file manager for all types of scrapers."""
    
    def __init__(self, scraper_type: 'Config.ScraperType'):
        """
        Initialize FileManager for a specific type of scraper.
        
        Args:
            scraper_type: Type of scraper (e.g., 'email', 'form', 'keyword')
        """
        self.scraper_type = scraper_type
        self.base_folders = {
            'html_element': Config.HTML_FOLDER_PATH / f"{scraper_type.value.capitalize()}ElementCapture",
            'screenshots': Config.SCREENSHOTS_FOLDER_PATH / f"{scraper_type.value.capitalize()}Screenshots"
        }
        if scraper_type != Config.ScraperType.TEMP:
            self.initialize_directories()

    @staticmethod
    def clear_subfolders():
        """Removes all subfolders under HTML_FOLDER_PATH and SCREENSHOTS_FOLDER_PATH."""
        try:
            for folder in [Config.HTML_FOLDER_PATH, Config.SCREENSHOTS_FOLDER_PATH]:
                if os.path.exists(folder):
                    for subfolder in os.listdir(folder):
                        subfolder_path = os.path.join(folder, subfolder)
                        if os.path.isdir(subfolder_path):
                            shutil.rmtree(subfolder_path)  # Remove subfolder
        except Exception as e:
            Logger.log(f"Error clearing subfolders: {e}")

    def initialize_directories(self) -> None:
        """Initializes base directories for the scraper type."""
        for folder in self.base_folders.values():
            os.makedirs(folder, exist_ok=True)
            Logger.log(f"Checked and ensured folder exists: {folder}")

    def get_subfolder_paths(self, url: str) -> Dict[str, str]:
        """
        Creates and returns paths to URL-specific subfolders for all folder types.
        
        Args:
            url: Website URL to create subfolders for
            
        Returns:
            Dictionary mapping folder types to their subfolder paths
        """
        subfolder_paths = {}
        for folder_type, base_folder in self.base_folders.items():
            subfolder_paths[folder_type] = self.create_subfolder(base_folder, url)
        return subfolder_paths

    def create_subfolder(self, base_folder: str, url: str) -> str:
        """
        Creates and returns path to a URL-specific subfolder.
        
        Args:
            base_folder: Base folder path
            url: Website URL to create subfolder for
            
        Returns:
            Path to the created subfolder
        """
        match = match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        subfolder_name = match.group(1).replace("/", "_") if match else "unknown"
        subfolder_path = os.path.join(base_folder, subfolder_name)
        
        if os.path.exists(subfolder_path):
            # for filename in os.listdir(subfolder_path):
            #     file_path = os.path.join(subfolder_path, filename)
            #     if os.path.isfile(file_path):
            #         os.remove(file_path)
            Logger.log(f"Subfolder exists: {subfolder_path}")
            return subfolder_path
        else:
            os.makedirs(subfolder_path, exist_ok=True)
            Logger.log(f"Created new subfolder: {subfolder_path}")
        
        return subfolder_path
    
    def capture_screenshots(self, 
                            driver: webdriver.Chrome, 
                            element: Any, 
                            url: str, 
                            element_type: str, 
                            subfolder_paths: Dict[str, str]) -> None:
        """Captures screenshots for the entire screen after scrolling to the element's location."""
        try:
            screenshot_path = os.path.join(
                subfolder_paths['screenshots'], 
                f"{element_type}_{uuid.uuid4().hex}.png"
            )

            # Scroll to the element's location
            ActionChains(driver).move_to_element(element).perform()
            time.sleep(1)

            # Capture a screenshot of the entire screen
            screenshot = driver.get_screenshot_as_png()

            # Save the screenshot as is
            with open(screenshot_path, "wb") as f:
                f.write(screenshot)
            Logger.log(f"Screenshot of the entire screen saved at: {screenshot_path}")
        except Exception as e:
            Logger.log(f"Error capturing screenshot: {str(e)}")

    @staticmethod
    def capture_page_source(page_source: str, url: str) -> None:
        """Saves the page source to a URL-specific subfolder under PrivacyPolicyPageSource."""
        try:
            # Base folder for privacy policy page sources
            base_folder = "PrivacyPolicyPageSource"
            os.makedirs(base_folder, exist_ok=True)

            # Create a URL-specific subfolder using the create_subfolder method
            temp_file_manager = FileManager(Config.ScraperType.TEMP)  # Temporary instance to use create_subfolder
            subfolder_path = temp_file_manager.create_subfolder(base_folder, url)

            # Generate file path for the page source
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            source_path = os.path.join(subfolder_path, f"source_{timestamp}.html")

            # Save the page source to the file
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(page_source)

            Logger.log(f"Page source saved at: {source_path}")
        except Exception as e:
            Logger.log(f"Error saving page source: {str(e)}")

    def capture_html_element(self, 
                             driver: webdriver.Chrome, 
                             element: Any, 
                             url: str, 
                             element_type: str, 
                             subfolder_paths: Dict[str, str]) -> None:
        """Saves the HTML element's outer HTML to a file."""
        try:
            element_path = os.path.join(
                subfolder_paths['html_element'], 
                f"{element_type}_{uuid.uuid4().hex}.html"
            )
            with open(element_path, 'w', encoding='utf-8') as f:
                f.write(element.get_attribute('outerHTML'))
            Logger.log(f"HTML element saved for {element_type} in {url}")
        except Exception as e:
            Logger.log(f"Error saving HTML element: {str(e)}")