# Keywords for filtering relevant privacy-related links
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
        lower_text = text.lower()
        lower_context = context.lower()
        lower_url = url.lower()

        url_parts = re.split(r'[/\?=#&._-]+', lower_url)

        return (
        any(
            re.search(rf"\b{re.escape(keyword)}\b", lower_text) or
            keyword.lower() in url_parts
            for keyword in self.PRIVACY_KEYWORDS__IN_ANCHOR_TEXT
        ) or
        any(
            re.search(rf"\b{re.escape(keyword)}\b", lower_context)
            for keyword in self.PRIVACY_KEYWORDS__IN_CONTEXT_TEXT
        )
    )

    def extract_anchor_tags_with_context(self) -> Union[List, Dict]:
        try:
            self.reset_page_state()
            anchor_tags = self.driver.find_elements(By.TAG_NAME, 'a')

            for anchor in anchor_tags:

                element_html = anchor.get_attribute('outerHTML')

                if element_html in self.processed_elements:
                    continue

                href = anchor.get_attribute('href')
                anchor_text = anchor.text.strip()

                if not href or href.startswith("#") or href.startswith("mailto:") or not anchor_text:
                    continue

                try:

                    parent = anchor.find_element(By.XPATH, '..')
                    context_text = parent.text.strip()

                    if self.is_privacy_related(href, anchor_text, context_text):

                        self.urls_with_text[href] = {
                            "text": anchor_text,
                            "context": context_text if context_text else "No context"
                        }
                        self.privacy_related_urls.add(href)

                    self.processed_elements.add(element_html)

                except StaleElementReferenceException:
                    Logger.log(f"Stale element encountered while processing anchor: {href}")
                    continue

            return [list(self.privacy_related_urls), self.urls_with_text]
        except Exception as e:
            Logger.log(f"Error in extract_anchor_tags_with_context: {str(e)}")
            return [[], {}]

    def is_context_relevant(self, anchor_text: str, surrounding_text: str) -> bool:
        if not surrounding_text.strip():
            return False

        context_embedding = self.model.encode(surrounding_text, convert_to_tensor=True)
        similarity_scores = util.pytorch_cos_sim(context_embedding, self.reference_embeddings)

        Logger.log(f"Similarity score  : {similarity_scores.max().item()}")
        return similarity_scores.max().item() > 0.6

    def reset_page_state(self):
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

                    context_text = parent_text if parent_text else "No context"

                    unique_key = f"{href}|{anchor_text[:30]}|{parent_text[:100]}"

                    Logger.log(f"Href text : {href[:max_length]}")
                    Logger.log(f"Anchor text : {anchor_text[:max_length]}")
                    Logger.log(f"Parent text : {parent_text[:max_length]}")

                    is_mailto_email = href.lower().startswith("mailto:") if href else False

                    if href and unique_key not in self.processed_elements:
                        if is_mailto_email or any(word.lower() in anchor_text.lower() for word in anchor_keywords):
                            if self.is_context_relevant(anchor_text, context_text):
                                self.urls_with_text[href] = self.urls_with_text.get(href, [])
                                self.urls_with_text[href].append({"text": anchor_text, "context": context_text})
                                self.privacy_related_urls.add(href)
                        self.processed_elements.add(unique_key)

                except StaleElementReferenceException:
                    Logger.log(f"Stale element encountered while processing anchor: {href}")
                    continue

            return [list(self.privacy_related_urls), self.urls_with_text]
        except Exception as e:
            Logger.log(f"Error in extract_anchor_tags: {str(e)}")
            return [[], {}]

    def extract_forms(self, website_url: str) -> dict:
        self.processed_elements.clear()

        forms = self.driver.find_elements(By.TAG_NAME, 'form')
        subfolder_paths = self.file_manager.get_subfolder_paths(website_url)

        form_count = 0

        for form in forms:

            form_html = form.get_attribute('outerHTML')

            if form_html in self.processed_elements:
                continue

            self.file_manager.capture_screenshots(
                self.driver, form, website_url, 'form', subfolder_paths
            )

            self.file_manager.capture_html_element(
                self.driver, form, website_url, 'form', subfolder_paths
            )

            self.processed_elements.add(form_html)
            form_count += 1

        return {website_url: form_count}
