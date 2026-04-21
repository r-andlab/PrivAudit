from enum import Enum
from pathlib import Path

class Config:
    """Configuration constants for the scraper."""

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    HTML_FOLDER_PATH = BASE_DIR / "results" / "html_element_captures"

    SCREENSHOTS_FOLDER_PATH = BASE_DIR / "results" / "screenshots"

    FILES = {
        'input_file': BASE_DIR / 'data' / 'privacy_policy_urls.txt',
        'output_file': BASE_DIR / 'results' / 'scraped_results.json'
    }

    class ScraperType(Enum):
        EMAIL = 'email'
        PHONE = 'phone'
        TEMP = 'temp'
        KEYWORD = 'keyword'
        ANCHOR_FORM = 'anchor_form'
        ANCHOR = 'anchor'

    # Timeout settings
    TIMEOUT_SECONDS = {
        'page_load': 60,
        'scroll': 30,
        'email_search': 60,
        'phone_search': 60,
        'keyword_search' : 60,
        'anchor_form_search' : 60
    }
    TIMEOUT_SECONDS['total_search'] = sum(TIMEOUT_SECONDS.values())