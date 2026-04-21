import re
from typing import Dict, List, Union
from .base_scraper import BaseScraper
from src.config import Config
from src.utils import FileManager, Logger

from selenium import webdriver
from src.timeout import TimeoutHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from sentence_transformers import SentenceTransformer, util

class AnchorFormScraper(BaseScraper):
    """Scraper class for extracting URLs, forms, and context for anchor tags from the Privacy Policy page."""
    
    # Keywords for filtering relevant privacy-related links
    PRIVACY_KEYWORDS__IN_ANCHOR_TEXT = {
        "Right of Deletion", "this form", "form", "here", "our form", "link", "help center", "delete", "just ask", "webform", "United States Regional Privacy Notice",
        "California Consumer Privacy Act", "CCPA", "contact us", "customer service", "U.S. Consumer Privacy Notice", "California Privacy Disclosure", "click here", "request", "privacy notice",
        "California Privacy Notice", "California Privacy Notices and Rights", "Privacy Policy Inquiries", "How to Reach Us"
    }

    PRIVACY_KEYWORDS__IN_CONTEXT_TEXT = {
        "Right of Deletion", "this form", "form", "our form", "help center", "delete", "exercise your rights", "CCPA", "California Consumer Privacy Act"
    }

    def __init__(self, driver: webdriver.Chrome):
        super().__init__(driver)
        self.file_manager = FileManager(scraper_type=Config.ScraperType.ANCHOR_FORM)
        self.urls_with_text = {}
        self.forms_data = {}
        self.processed_elements = set()
        self.privacy_related_urls = set()
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.PRIVACY_KEYWORDS__IN_ANCHOR_TEXT = {keyword.lower() for keyword in self.PRIVACY_KEYWORDS__IN_ANCHOR_TEXT}
        self.PRIVACY_KEYWORDS__IN_CONTEXT_TEXT = {keyword.lower() for keyword in self.PRIVACY_KEYWORDS__IN_CONTEXT_TEXT}
        self.reference_texts = [
            "Users have the right to access, delete, correct, and opt out of the sale or sharing of their personal data under applicable privacy laws.",
            "California residents can request access to their personal data collected, including sources, purposes, and third-party disclosures.",
            "You may request deletion of your personal information unless an exception applies.",
            "Users may opt out of targeted advertising and cross-context behavioral advertising by adjusting their privacy settings.",
            "Users can correct inaccurate personal information stored in their profile.",
            "You can request a copy of your personal data through the 'Download Your Data' tool or by contacting support.",
            "To delete account data and close an account, follow the steps outlined on the support page.",
            "Users may withdraw their consent for the processing of their personal data if it was collected based on consent.",
            "Consumers can submit privacy-related requests through the 'Your Privacy Choices' page.",
            "Users can appeal a denied privacy request by contacting customer support.",
            "Authorized agents may submit privacy requests on behalf of consumers, but must provide verification.",
            "Users can view privacy metrics related to consumer data requests from the previous year.",
            "Request that we do not sell or share your personal data with third parties.",
            "Utilize our opt-out mechanism to prevent data sharing.",
            "Enable Global Privacy Control (GPC) signals to express your privacy preferences.",
            "We recognize and honor Global Privacy Control signals sent by your browser.",
            "File a request to opt out of interest-based advertising.",
            "Do Not Sell or Share My Personal Information.",
            "You may opt out of the sale of personal data to third-party advertisers.",
            "Turn off personalized ads based on your browsing behavior.",
            "To stop receiving targeted ads, adjust your privacy settings.",
            "Your opt-out preference will apply to all data processing activities involving your personal information.",
            "request access, correct, delete, or opt out of the sale of your personal data",
            "To exercise these rights please visit your account settings",
            "To delete your account and associated personal data, click Delete Account in Account Settings.",
            "If you would like to access your personal information or obtain a copy of your personal information in a portable manner"
        ]
        self.reference_embeddings = self.model.encode(self.reference_texts, convert_to_tensor=True)
    
    def is_privacy_related(self, url: str, text: str, context: str) -> bool:
        """Check if the URL, text, or context contains privacy-related keywords."""
        lower_text = text.lower()
        lower_context = context.lower()
        lower_url = url.lower()

        # Split URL on special characters
        url_parts = re.split(r'[/\?=#&._-]+', lower_url)

        return (
        any(
            re.search(rf"\b{re.escape(keyword)}\b", lower_text) or
            keyword.lower() in url_parts  # Whole word match in URL
            for keyword in self.PRIVACY_KEYWORDS__IN_ANCHOR_TEXT
        ) or
        any(
            re.search(rf"\b{re.escape(keyword)}\b", lower_context)
            for keyword in self.PRIVACY_KEYWORDS__IN_CONTEXT_TEXT
        )
    )

    # @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['anchor_form_search'], "Anchor Form search")

    def extract_anchor_tags_with_context(self) -> Union[List, Dict]:
        """
        Extracts privacy-related anchor tags from the current page.
        Returns a set of relevant URLs for further processing.
        """
        try:
            self.reset_page_state()
            anchor_tags = self.driver.find_elements(By.TAG_NAME, 'a')
            
            for anchor in anchor_tags:
                # Get the outerHTML to uniquely identify the element
                element_html = anchor.get_attribute('outerHTML')
                
                # Skip if already processed on this page
                if element_html in self.processed_elements:
                    continue
                
                href = anchor.get_attribute('href')
                anchor_text = anchor.text.strip()
                
                # Basic filtering conditions
                if not href or href.startswith("#") or href.startswith("mailto:") or not anchor_text:
                    continue
                
                try:
                    # Get context from parent element
                    parent = anchor.find_element(By.XPATH, '..')
                    context_text = parent.text.strip()
                    
                    # Check if URL is privacy-related
                    if self.is_privacy_related(href, anchor_text, context_text):
                        # Store URL details
                        self.urls_with_text[href] = {
                            "text": anchor_text,
                            "context": context_text if context_text else "No context"
                        }
                        self.privacy_related_urls.add(href)
                    
                    # Mark as processed for this page
                    self.processed_elements.add(element_html)
                    
                except StaleElementReferenceException:
                    Logger.log(f"Stale element encountered while processing anchor: {href}")
                    continue
            
            return [list(self.privacy_related_urls), self.urls_with_text]
        except Exception as e:
            Logger.log(f"Error in extract_anchor_tags_with_context: {str(e)}")
            return [[], {}]
        
    def is_context_relevant(self, anchor_text: str, surrounding_text: str) -> bool:
        """Checks if the anchor context is relevant using sentence similarity."""
        if not surrounding_text.strip():
            return False  # Skip empty or irrelevant surrounding text
        
        context_embedding = self.model.encode(surrounding_text, convert_to_tensor=True)
        similarity_scores = util.pytorch_cos_sim(context_embedding, self.reference_embeddings)
        
        Logger.log(f"Similarity score  : {similarity_scores.max().item()}")
        return similarity_scores.max().item() > 0.6  # Threshold for relevance
    
    def reset_page_state(self):
        """Resets the state for processing a new page."""
        self.processed_elements.clear()
        self.privacy_related_urls.clear()
        self.urls_with_text = {}
        self.forms_data = {}

    def extract_anchor_tags(self) -> Union[List, Dict]:
        try:
            self.reset_page_state()
            anchors = self.driver.find_elements(By.TAG_NAME, 'a')

            anchor_keywords = {"Download Your Data", "Right of Deletion", "contact us", "here", "account settings",
                            "click here", "Request Data", "Delete Account", "Notice of Right to Opt-Out", 
                            "Help Center", "Your Privacy Choices", "support page", "chat bot", "opt-out"}

            for anchor in anchors:
                try:
                    max_length = 50
                    href = anchor.get_attribute("href") or ""

                    anchor_text = (anchor.text or anchor.get_attribute("innerText") or "").strip()

                    parent_text = anchor.find_element(By.XPATH, '..').text.strip() if anchor.find_element(By.XPATH, '..').text else ""
                    # try:
                    #     parent_element = anchor.find_element(By.XPATH, '..')
                    #     parent_text = (parent_element.text or "").strip()

                    #     # If parent text is empty, check for text inside child <span> elements
                    #     if not parent_text:
                    #         span_elements = parent_element.find_elements(By.TAG_NAME, 'span')
                    #         span_text_list = [span.text.strip() for span in span_elements if span.text.strip()]
                    #         parent_text = " ".join(span_text_list)  # Combine text from spans if found

                    # except Exception as e:
                    #     Logger.log(f"Exception while fetching parent: {href}")
                    #     parent_text = ""
                    context_text = parent_text if parent_text else "No context"

                    # Create a unique key using href, anchor text, and parent text (limit to 30 chars)
                    unique_key = f"{href}|{anchor_text[:30]}|{parent_text[:100]}"

                    Logger.log(f"Href text : {href[:max_length]}")
                    Logger.log(f"Anchor text : {anchor_text[:max_length]}")
                    Logger.log(f"Parent text : {parent_text[:max_length]}")

                    is_mailto_email = href.lower().startswith("mailto:") if href else False

                    if href and unique_key not in self.processed_elements:
                        if is_mailto_email or any(word.lower() in anchor_text.lower() for word in anchor_keywords):
                            if self.is_context_relevant(anchor_text, context_text):
                                self.urls_with_text[href] = self.urls_with_text.get(href, [])  # Ensure list structure
                                self.urls_with_text[href].append({"text": anchor_text, "context": context_text})
                                self.privacy_related_urls.add(href)
                        self.processed_elements.add(unique_key)  # Track this unique instance

                except StaleElementReferenceException:
                    Logger.log(f"Stale element encountered while processing anchor: {href}")
                    continue

            return [list(self.privacy_related_urls), self.urls_with_text]
        except Exception as e:
            Logger.log(f"Error in extract_anchor_tags: {str(e)}")
            return [[], {}]

    def extract_forms(self, website_url: str) -> dict:
        """Extracts all form tags, captures screenshots and HTML, and sets a flag if forms are found."""
        self.processed_elements.clear()
        
        forms = self.driver.find_elements(By.TAG_NAME, 'form')
        subfolder_paths = self.file_manager.get_subfolder_paths(website_url)
        
        form_count = 0  # Track number of unique forms processed

        for form in forms:
            # Get the outerHTML to uniquely identify the form
            form_html = form.get_attribute('outerHTML')

            # Skip if form was already processed
            if form_html in self.processed_elements:
                continue  

            # Capture screenshots and HTML only if form is visible
            # if form.is_displayed():
            self.file_manager.capture_screenshots(
                self.driver, form, website_url, 'form', subfolder_paths
            )

            self.file_manager.capture_html_element(
                self.driver, form, website_url, 'form', subfolder_paths
            )

            # Mark this form as processed and increase count
            self.processed_elements.add(form_html)
            form_count += 1  
        
        # Store a simple JSON to indicate if forms were found or not
        return {website_url: form_count}