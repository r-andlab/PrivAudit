from typing import Dict, List, Union
from urllib.parse import urlparse, urlunparse
from src.config import Config
from src.scrapers import EmailScraper,PhoneScraper, KeywordScraper, AnchorFormScraper, AnchorScraper
from src.timeout import TimeoutException
from src.utils.json_manager import JsonManager
from .page_loader import PageLoader
from src.utils import Logger
from selenium import webdriver
from src.dto import ResultDTO

class WebsiteProcessor:
    """Manages the processing of websites with support for initial and deep scanning."""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.page_loader = PageLoader(driver)
        self.email_scraper = EmailScraper(driver)
        self.phone_scraper = PhoneScraper(driver)
        self.keyword_scraper = KeywordScraper(driver)
        self.anchor_form_scraper = AnchorFormScraper(driver)
        self.anchor_scraper = AnchorScraper(driver)
        self.processed_urls = set()  # Track all processed URLs
        self.result_dto = None
        self.json_manager = JsonManager(Config.FILES['output_file'])

    def filter_duplicate_urls(self, privacy_urls: list) -> None:
        """Removes URLs from privacy_urls if their normalized form is already in processed_urls."""
        
        def normalize_url(url: str) -> str:
            """Removes query parameters and fragments from a URL."""
            parsed_url = urlparse(url)
            return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))

        # Normalize all URLs in privacy_urls
        privacy_urls[:] = [url for url in privacy_urls if normalize_url(url) not in self.processed_urls]

    def is_new_url(self, url: str) -> bool:
        """Checks if a normalized URL is already in processed_urls.

        Returns:
            bool: False if the normalized URL is already in processed_urls, True otherwise.
        """

        def normalize_url(url: str) -> str:
            """Removes query parameters and fragments from a URL."""
            parsed_url = urlparse(url)
            return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        
        if url.startswith("mailto:"):
            return False
        
        # Normalize the given URL
        normalized_url = normalize_url(url)

        # Return False if already processed, True otherwise
        return normalized_url not in self.processed_urls
        
    def process_initial_scan(self, website_url: str) -> List[str]:
        """Performs initial scan of the website, collecting all basic data."""

        privacy_urls = set()  # Store privacy-related URLs for deep scanning

        self.result_dto = ResultDTO(website_url)
        
        try:
            if not self.page_loader.load_url(website_url):
                Logger.log(f"Skipping {website_url} due to failed initial load")
                return list(privacy_urls)

            # Attempt page load and scroll
            self._perform_page_preparation(website_url)
            
            # Run one-time scrapers
            emails = self._run_email_scraper(website_url)
            self.result_dto.add_emails(emails)

            phone_numbers = self._run_phone_scraper(website_url)
            self.result_dto.add_phonenumbers(phone_numbers)

            keywords = self._run_keyword_scraper(website_url)
            self.result_dto.add_keywordcount_version(keywords)
            
            # Initial form and URL collection
            [privacy_urls, urls_with_text] = self._run_initial_anchor_tag_scan(website_url)
            self.result_dto.add_urls_with_text_version({website_url: urls_with_text})

            # forms_data = self._run_form_scan(website_url)
            # self.result_dto.add_forms_data_version(forms_data)

            # Mark as processed
            self.processed_urls.add(website_url)
            
        except Exception as e:
            Logger.log(f"process_initial_scan() -> Error processing {website_url}: {str(e)}")
            
        return privacy_urls
    
    def process_deep_scan(self, privacy_urls: set, max_depth: int = 2) -> None:
        """Performs deep scanning of privacy-related URLs."""
        try:
            for url in privacy_urls:
                if self.is_new_url(url):  
                    self._process_url_recursively(url, current_depth=0, max_depth=max_depth)
                
        except Exception as e:
            Logger.log(f"process_deep_scan() -> Error during deep scan: {str(e)}")
    
    def _process_url_recursively(self, url: str, current_depth: int, max_depth: int) -> None:
        """Recursively process URLs up to max_depth."""
        if current_depth >= max_depth or url in self.processed_urls:
            return
            
        try:
            # Prepare page
            if not self.page_loader.load_url(url):
                return
            self._perform_page_preparation(url)
            
            # Run anchor/form scraper
            [new_urls, urls_with_text] = self._run_initial_anchor_tag_scan(url)

            forms_found = self._run_form_scan(url)
            self.result_dto.add_forms_data_version(forms_found)
            
            # Mark as processed
            self.processed_urls.add(url)

            self.filter_duplicate_urls(new_urls)

            urls_with_text = {key: value for key, value in urls_with_text.items() if key in new_urls}
            self.result_dto.add_urls_with_text_version({url : urls_with_text})
            
            # Recursively process new URLs
            Logger.log(f"_process_url_recursively() -> Found new privacy urls: {new_urls} within {url}")
            for new_url in new_urls:
                if new_url not in self.processed_urls:
                    self._process_url_recursively(new_url, current_depth + 1, max_depth)
                    
        except Exception as e:
            Logger.log(f"_process_url_recursively() -> Error processing {url}: {str(e)}")
    
    def _perform_page_preparation(self, website_url: str) -> None:
        """Prepares the page by loading and scrolling."""
        try:
            self.page_loader.attempt_page_load()
        except TimeoutException as e:
            Logger.log(f"PageLoader._perform_page_preparation() -> Timeout while waiting for the page to load {website_url}: {str(e)}")

        try:
            self.page_loader.attempt_scroll()
        except TimeoutException as e:
            Logger.log(f"PageLoader._perform_page_preparation() -> Timeout while scrolling through the page {website_url}: {str(e)}")

        # self.page_loader.save_page_source(website_url)
    
    def _run_email_scraper(self, website_url: str) -> List[str]:
        """Runs email scraper and returns results."""
        try:
            emails = self.email_scraper.search_emails(website_url)
        except TimeoutException:
            emails = self.email_scraper.get_found_emails_as_list()
            
        # if emails:
        #     self.email_scraper.json_manager.update_results(website_url, emails, 'emails')
        return emails
    
    def _run_phone_scraper(self, website_url: str) -> List[str]:
        """Runs phone number scraper and returns results."""
        try:
            phone_numbers = self.phone_scraper.search_phone_numbers(website_url)
        except TimeoutException:
            phone_numbers = self.phone_scraper.get_found_numbers_as_list()
            
        # if phone_numbers:
        #     self.phone_scraper.json_manager.update_results(website_url, phone_numbers, 'phonenumbers')
        return phone_numbers
    
    def _run_keyword_scraper(self, website_url: str) -> dict:
        """Runs keyword scraper and returns results."""
        try:
            keywords = self.keyword_scraper.search_keywords(website_url)
        except TimeoutException:
            keywords = self.keyword_scraper.keyword_counts
            
        # if keywords:
        #     self.keyword_scraper.json_manager.update_results(website_url, keywords, 'keywordcount')
        return keywords
    
    def _run_initial_anchor_tag_scan(self, website_url: str) -> Union[List, Dict]:
        """Runs initial anchor/form scan and returns privacy-related URLs."""
        try:
            # Extract privacy-related URLs
            # return self.anchor_form_scraper.extract_anchor_tags_with_context()
        
            # return self.anchor_form_scraper.extract_anchor_tags()
        
            return self.anchor_scraper.extract_anchor_tags(website_url)
            
        except TimeoutException as e:
            Logger.log(f"Timeout during anchor/form scan for {website_url}: {str(e)}")
            return [[], {}]
        
    def _run_form_scan(self, website_url: str) -> dict:
        """Runs form scan"""
        try:
            # Extract privacy-related URLs
            return self.anchor_form_scraper.extract_forms(website_url)
            
        except TimeoutException as e:
            Logger.log(f"Timeout during anchor/form scan for {website_url}: {str(e)}")
            return {}