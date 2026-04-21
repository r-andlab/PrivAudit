from typing import Dict, List, Optional, Tuple, Union
from .base_scraper import BaseScraper
from src.config import Config
from src.utils import FileManager, Logger
from urllib.parse import urlparse, urlunparse

from selenium import webdriver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from sentence_transformers import SentenceTransformer, util

class AnchorScraper(BaseScraper):
    """Scraper class for extracting URLs, forms, and context for anchor tags from the Privacy Policy page."""

    def __init__(self, driver: webdriver.Chrome):
        super().__init__(driver)
        self.file_manager = FileManager(scraper_type=Config.ScraperType.ANCHOR_FORM)

        self.urls_with_text = {}
        self.forms_data = {}
        self.processed_elements = set()
        self.privacy_related_urls = set()

        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # Initialize category embeddings
        self.initialize_category_embeddings()

    def reset_page_state(self):
        """Resets the state for processing a new page."""
        self.processed_elements.clear()
        self.privacy_related_urls.clear()
        self.urls_with_text = {}
        self.forms_data = {}

    def is_redirect_to_same_url(self, href: str, website_url: str) -> bool:

        def normalize_url(href: str) -> str:
            """Removes query parameters and fragments from a URL."""
            parsed_url = urlparse(href)
            return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        
        if href.startswith("mailto:"):
            return False
        
        # Normalize the given URL
        normalized_url = normalize_url(href)

        return normalized_url == website_url
    
    def initialize_category_embeddings(self):
        """Initializes privacy-related categories with reference texts and precomputes their embeddings."""
        
        self.CATEGORY_STATEMENTS = {
            "Right_To_Delete": [
                "To delete your account and associated data, follow the instructions provided on our support page."
                "Your account deletion request will remove personal data, including User Data, Usage Data, and other stored information."
                "For additional deletion requests beyond account closure, contact our support team or use the chat bot."
                "If you need assistance in removing personal data, visit our Help Center or submit a request."
                "For questions regarding data deletion, you can reach out to customer support through the available contact options."
                "Account deletion processes may vary based on the platform you are using to submit the request."
                "If you delete your account, you will also be removed from our email marketing and newsletter lists."
                "Account deletion will remove you from our registered user database, except where legal restrictions apply."
                "You have the right to request deletion of your personal data.",
                "Users may request that we delete their personal information.",
                "To delete your account and associated personal data, visit account settings."
                "Request Deletion of your personal information, subject to certain exceptions prescribed by law."
                "Request Deletion of your personal information. This right may be limited to the extent that we are permitted or required by applicable law to retain certain information."
                "If you request deletion of your Personal Information, you may no longer be able to use or access all features of the Services as a Registered User."
                "If you decide to use or access the Services again, we may consider this a new account, and may collect Personal Information associated with that account in accordance with this Privacy Policy."
                "The right to request that we delete your personal information that we have collected from you."
                "Once we receive and confirm your verifiable consumer request, we will delete (and direct our service providers to delete) your personal information from our records, unless an exception applies."
                "We may retain personal information for certain important purposes, such as to protect our business, systems, and users from fraudulent activity, address technical issues, comply with law enforcement requests, or for scientific or historical research."
                "To make a deletion request, please visit Your Privacy Choices."
                "You can have your information deleted. In your settings, select ‘Delete your data and account’ and follow the instructions."
                "You may submit a verifiable request that we delete Personal Information we have collected from you."
                "In certain circumstances, you have the right to request the deletion of your information, except information we are required to retain by law, regulation, or to protect the safety, security, rights, and integrity of Etsy."
                "Closing your account may not free up your email address, username, or shop name for reuse on a new account."
                "To request deletion of your account data from Spotify and close your account, follow the steps on our support page."
                "For any other deletion requests, you can contact us or reach out to customer support via our chat bot."
                "You may request that we delete the Personal Data and/or Personal Information we have collected from you."
                "In some instances, we may decline to honor your request or only honor your request in part, where we are unable to verify your identity or an exception to this right applies."
                "You may delete your account information at any time from the user preferences page."
                "When you delete your account, your profile is no longer visible to other users and disassociated from content you posted under that account."
                "Posts, comments, and messages you submitted prior to deleting your account will still be visible to others unless you first delete the specific content."
                "After you submit a request to delete your account, our purge script commences the deletion process within 90 days."
                "After running our purge script, we will not be able to provide access to deleted data."
                "We may also retain certain information about you for legitimate business purposes or as required by applicable law."
                "You can request us to delete all the information we have collected about you."
                "By exercising your right to deletion, you may lose access to your account and any purchases, points, or features associated with it."
                "If you wish to cancel your account or request that we no longer use some or all of your information to provide you services, contact us via our contact details."
                "If you want to delete your Account, you can do so from your Account Settings."
                "Deleting your Account may not fully remove the content you have published from our systems, as caching, backups, copies, or references to your Account Information may not be immediately removed."
                "Some of the public activity on your Account prior to deletion (such as reblogs of your blog posts) may remain stored on our servers and accessible to the public."
                "You may request that we delete your personal data."
            ],
            "Generic_Request": [
                "Submit a request to access or delete your data via our privacy portal or email."
                "To exercise your rights, visit the provided webform or contact us at the listed email."
                "You can request data access or deletion through our official privacy request page."
                "Click here to manage your privacy settings and submit requests after logging into your account."
                "To initiate a privacy request, use our web form or send an email to our support team."
                "Access our CCPA request page to submit a request for data access or deletion."
                "You may request to review or remove your data via our designated privacy contact methods."
                "Privacy requests can be submitted through our online request form or by contacting us directly."
                "To make changes to your personal data, use the web form or reach out via email."
                "Exercise your privacy rights by clicking the link to submit your request through our official channels."
                "You can control how much personal information, such as your name, is visible in your profile and posts through Privacy Settings."
                "Visit our Jurisdiction-Specific Disclosures page for information on your region-specific privacy rights and options."
                "Members can access their personal information directly from their accounts, while non-members can inquire via email."
                "Certain jurisdictions allow users to opt out of personalized advertising through specific mechanisms outlined in our policies."
                "Depending on your location, you may have legal rights to access and download your personal data."
                "If you would like to exercise any of these rights, please submit a data request"
                "You can modify or update certain personal details in your account settings."
                "A record of previous information updates may be retained for reference and compliance purposes."
                "Your account settings allow access to personal details such as name, address, and payment methods."
                "Click here to view examples of the types of information you can review and update."
                "Users can access and edit their stored profile information within their account dashboard."
                "Certain account details, including payment preferences, can be managed via the settings page."
                "For transparency, we may maintain copies of prior versions of your data when updates are made."
                "Visit our account management page to review or change your personal information."
                "Your account may contain editable information such as contact details and billing preferences."
                "To see what information you can access and modify, check our privacy resources or settings page."
                "If you access our services without an account, we may not be able to verify or fulfill your privacy request."
                "We only process data requests linked to a verifiable email address to ensure privacy and security."
                "Identity verification is a required step before we take action on any privacy-related request."
                "Requests must be submitted using the email address associated with the personal information in question."
                "We verify requests by sending an email to the provided address and requiring a confirmation response."
                "In certain cases, additional information may be requested to confirm your identity before processing your request."
                "Requests must be submitted using the email address associated with the personal information in question."
                "When submitting a request, clearly specify the details, such as data modifications, suppression, or usage restrictions."
                "To exercise your privacy choices, please complete the designated request form or call our toll-free number."
                "For further guidance on privacy requests, please consult our Help Center or use the contact details below."
                "If you require additional support, please use the provided contact options, and we will review your request as required."
                "You may also reach out via email or other listed contact methods to have your request reviewed."
                "If you need assistance with submitting a privacy request, please refer to the available contact options."
                "You can also contact us using the provided contact details, and we will review your request as required by law."
                "Information about those rights, and how to exercise them, can be found here"
                "Depending on your jurisdiction, you may have privacy rights that allow you to access, modify, or delete your data."
                "You can manage your data preferences in your account settings or seek further assistance in our Help Center."
                "Your privacy rights under local laws may include access, correction, deletion, or restriction of data processing."
                "If you need help managing your data or understanding your rights, please check our Help Center or contact us."
                "To exercise your privacy rights, visit your account settings or consult our Help Center for further assistance."
                "Residents of certain regions, such as the EEA, UK, and US, may have additional rights regarding their personal information."
                "Your ability to control your data may vary based on your location (e.g., EEA, Switzerland, UK, US) and applicable laws."
                "To exercise your rights, please contact us at [email address] or submit a request through our designated form."
                "You must have access to the email associated with your account to verify your identity before your request can be processed."
                "If you need assistance in exercising your privacy rights, you can reach out to us via the provided contact details."
                "Please visit our privacy support center to find the appropriate forms and instructions for submitting a request."
                "Your request may require identity verification via the email address linked to your account."
                "To make changes to your data, including rectification or deletion, follow the instructions on our privacy request page."
                "If you are unable to complete your request using the available options, please contact us for further guidance."
                "If you would like to access, download, delete, rectify, update, ask a question about, or withdraw consent regarding your data, please submit your request through our automated, self-service system."
                "To exercise these rights, please visit your account settings."
                "If you have questions or cannot submit a request through the provided mechanisms, you may contact us via email."
                "If your request is denied, you may appeal by contacting us via email."
                "Before processing your request, we may need to verify your identity through your account or a registered email."
                "To submit a request regarding your personal information, email us from the verified email address associated with your account."
                "If you still need help, visit our Help Center or contact us at"
                "To exercise your rights described above, please submit a request in one of the following ways."
                "click here and follow the instructions, or email us with details of your request."
                "To exercise any of these rights, please use the indicated forms or links, where applicable."
                "Alternatively, you can exercise any of the rights above, subject to applicable law, through the contact options"
                "In order to make privacy requests, please visit our Privacy Portal and fill out the form."
                "To make a Request to Know, a Request for a Copy, a Request to Correct, or a Request to Delete, please use the Help Center or contact us"
            ],
            "Right_To_Know": [
                "Download your information"
                "You can access your information"
                "What information can i access"
                "Export your data"
                "Download a copy of your information"
                "We’ll give you a report on the personal information that we have about you. Just submit an access request to get started."
                "To obtain a copy of your personal data, use the ‘Download Your Data’ tool in your account settings."
                "You may also contact us directly to request a copy of your data under applicable privacy laws."
                "When you request a data download, we provide information as required by legal regulations."
                "For additional details on how we handle your personal data, feel free to reach out to us."
                "To receive an export of your personal information, navigate to your privacy settings and follow the instructions."
                "We offer tools to help you access and download your personal data in compliance with relevant privacy laws."
                "To review your stored data, you can either use our automated download feature or submit a formal request."
                "If you require more insights on how we manage your data, please visit our privacy policy or contact us."
                "You can learn more about the information we have collected or inferred about you and request access to additional information here."
                "You can download a copy of your information, such as your posts, by following the instructions here"
                "Individuals can access and update certain personal information through designated account pages, while prior versions may be retained for records"
                "View a summary of your information. We’ve grouped it together to help you find what you’re looking for."
                "Download a copy of your information"
                "You have the right to know what personal data we have collected.",
                "Users can request access to the categories of personal data collected about them.",
                "California residents may request a copy of their personal data."
                "Know about your personal information we have collected, disclosed, or sold in the last 12 months, upon verification of your identity."
                "You may have the right in some cases to receive or have your electronic personal information transferred to another party."
                "Access personal information about you consistent with legal requirements."
                "Job seekers can access or obtain a copy of their personal information in a portable manner by logging into their password-protected account and submitting a data request."
                "Clients can request access to their personal information by sending an email from the address associated with their account, and upon verification, receive a downloadable copy."
                "Users of affiliated sites can access or obtain a copy of their personal information by logging into their password-protected account and submitting a request through the user settings page."
                "Consumers may submit a request via email to access or obtain a copy of their personal information in a portable manner, provided they verify their identity."
                "Requests for access to specific personal information will require identity verification by matching submitted details with information in the system."
                "California residents have the right to request disclosure of the personal information collected, used, disclosed, shared, or sold."
                "Individuals may request access to the specific pieces and/or categories of personal information collected about them."
                "If identity verification is successful, personal information may be provided, but certain details may be withheld if the disclosure poses a risk."
                "If identity verification fails, specific pieces of personal information will not be disclosed, and the requester will be informed."
                "Individuals can request access to the information collected and held about them in a portable format."
                "Individuals may submit a verifiable request to learn about information practices and access specific pieces of personal information collected about them."
                "Individuals can access certain information associated with their account by visiting their account privacy settings."
                "Individuals may request a copy of their personal information in an easily accessible format, along with an explanation of how that information is used."
                "Individuals have the right to receive certain personal information in a structured, commonly used, and machine-readable format for portability."
                "Individuals may transmit their personal information to another entity if requested."
                "Individuals can request a copy of their personal data through a designated account privacy tool or by contacting the company directly."
                "Upon requesting a data download, individuals will receive the personal information the company is required to provide under applicable laws."
                "Individuals may contact the company to learn more about how their personal data is processed."
                "Individuals may request access to specific pieces of personal data collected and maintained about them in a portable format."
                "Individuals may request access to the categories of personal data collected and their sources."
                "Individuals may request information on the business or commercial purpose for collecting, disclosing, or selling their personal data."
                "Individuals may request details on the categories of personal data that were sold, shared, or disclosed, along with the third parties involved."
                "Requests may be declined or only partially fulfilled if identity verification fails or if an exception applies."
                "Individuals can access, change, or correct certain personal information through the provided services."
                "Individuals may request a copy of the personal information maintained about them by following a designated process."
                "Individuals can request a copy of the personal information collected about them."
                "Individuals have the right to know what personal information is collected, processed, shared, or sold."
                "This policy is intended to provide transparency regarding the collection and use of personal data."
                "Individuals can access much of their personal information by logging into their account."
                "Individuals without an account or requiring additional access may request a copy of their information."
                "Where legally required, personal information can be provided in an easily accessible format."
                "Assistance may be provided for transferring certain personal information to third parties."
                "Individuals may request to know whether their personal data is being processed."
                "California residents may request disclosure of personal data collected in the past 12 months, including its sources and categories."
                "Individuals may request information on the business or commercial purpose for collecting, selling, or sharing their personal data."
                "Individuals may request details on the categories of personal data sold or shared and the third parties involved."
                "Individuals may request details on the categories of personal data disclosed and the third parties to whom it was disclosed."
                "Individuals may request a copy of their personal data, including in a portable and readily usable format where applicable."
                "Port your information"
                "In certain cases and subject to applicable law, you have the right to port your information"
            ],
            "Right_To_Correct": [
                "Users may correct inaccurate personal information stored in their profile.",
                "You have the right to request corrections to your personal data.",
                "If you believe your information is incorrect, you can update it in your account settings."
            ],
            "Opt_Out": [
                "You can opt out of the sale of your personal data.",
                "Users have the right to opt out of cross-context behavioral advertising.",
                "To opt out of targeted advertising, visit your privacy settings."
            ],
            "Right_To_Limit": [
                "You may limit the use and disclosure of sensitive personal data.",
                "Users can restrict how their sensitive personal data is processed.",
                "To limit data sharing, adjust your privacy settings."
            ],
            "Agents": [
                "Authorized agents may submit privacy requests on behalf of consumers.",
                "Users can designate an agent to make privacy-related requests.",
                "To authorize an agent, you must provide verification."
            ]
        }

        # Precompute category embeddings for similarity comparison
        self.category_embeddings = {
            category: self.model.encode(statements, convert_to_tensor=True)
            for category, statements in self.CATEGORY_STATEMENTS.items()
        }
    
    def get_best_matching_category(self, context_text: str) -> Tuple[Optional[str], float]:
        """Finds the most relevant category based on similarity score."""
        if not context_text.strip():
            return None, 0.0  # Skip empty context

        context_embedding = self.model.encode(context_text, convert_to_tensor=True)

        best_category = None
        highest_score = 0.0
        threshold = 0.65

        for category, embeddings in self.category_embeddings.items():
            similarity_scores = util.pytorch_cos_sim(context_embedding, embeddings)
            max_score = similarity_scores.max().item()
            Logger.log(f"Score is : {max_score} for category : {category}")

            if max_score > highest_score and max_score >= threshold:
                highest_score = max_score
                best_category = category

        return best_category, highest_score

    def extract_anchor_tags(self, website_url: str) -> Union[List, Dict]:
        try:
            self.reset_page_state()
            
            # Find all elements that contain an <a> tag
            parent_elements = self.driver.find_elements(By.XPATH, "//*[a]")  # Any element that has an <a> tag inside

            anchor_keywords = {"Download Your Data", "Right of Deletion", "contact us", "here", "account settings",
                            "click here", "Request Data", "Delete Account", "Notice of Right to Opt-Out", 
                            "Help Center", "Your Privacy Choices", "support page", "chat bot", "opt-out"}

            for parent in parent_elements:
                try:
                    anchor_tags = parent.find_elements(By.TAG_NAME, "a")  # Find all anchor tags inside this element

                    for anchor in anchor_tags:
                        max_length = 50
                        
                        href = anchor.get_attribute("href") or ""
                        if not href:
                            continue

                        anchor_text = (anchor.text or anchor.get_attribute("innerText") or "").strip()

                        skip_keywords = {"contact us", "contact", "How to Reach Us"}
                        skip_keywords_for_href = {"form", "webform"}

                        if self.is_redirect_to_same_url(href, website_url) and anchor_text.lower() not in skip_keywords:
                            continue

                        parent_text = parent.text.strip() if parent.text else ""

                        # Create a unique key using href, anchor text, and parent text (limit to 30 chars)
                        unique_key = f"{href}|{anchor_text[:30]}|{parent_text[:100]}"

                        Logger.log(f"Href text : {href[:max_length]}")
                        Logger.log(f"Anchor text : {anchor_text[:max_length]}")
                        Logger.log(f"Parent text : {parent_text[:max_length]}")
                       
                        if any(keyword in href for keyword in skip_keywords_for_href):
                            matched_category, similarity_score = "Bypass", 0.0
                        else:
                             # Find the most relevant category for the context
                            matched_category, similarity_score = self.get_best_matching_category(parent_text)

                        if unique_key not in self.processed_elements:
                            if matched_category:  # Store only if a category is identified
                                self.urls_with_text[href] = self.urls_with_text.get(href, [])  # Ensure list structure
                                self.urls_with_text[href].append({
                                    "text": anchor_text,
                                    "context": parent_text,
                                    "category": matched_category,
                                    "similarity_score": similarity_score
                                })
                                self.privacy_related_urls.add(href)

                            self.processed_elements.add(unique_key)  # Track this unique instance

                except StaleElementReferenceException:
                    Logger.log(f"Stale element encountered while processing anchor: {href}")
                    continue

            return [list(self.privacy_related_urls), self.urls_with_text]
        except Exception as e:
            Logger.log(f"Error in extract_anchor_tags: {str(e)}")
            return [[], {}]