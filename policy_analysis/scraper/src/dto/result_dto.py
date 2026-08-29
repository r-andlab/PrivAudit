# src/data/data_object.py
from typing import Dict, List, Union

class ResultDTO:

    def __init__(self, url: str):
        self.url: str = url
        self.emails: List[str] = []
        self.phonenumbers: List[str] = []
        self.keywordcount_versions: List[Dict[str, Dict[str, int]]] = []
        self.urls_with_text_versions: List[Dict[str, Dict[str, List[Dict[str, str]]]]] = []
        self.forms_data_versions: List[Dict[str, int]] = []

    def add_emails(self, emails: List[str]):
        self.emails.extend(emails)

    def add_phonenumbers(self, phonenumbers: List[str]):
        self.phonenumbers.extend(phonenumbers)

    def add_keywordcount_version(self, keywordcount: Dict[str, Dict[str, int]]):
        self.keywordcount_versions.append(keywordcount)

    def add_urls_with_text_version(self, urls_with_text: Dict[str, Dict[str, List[Dict[str, str]]]]):
        self.urls_with_text_versions.append(urls_with_text)

    def add_forms_data_version(self, forms_data: Dict[str, int]):
        if isinstance(forms_data, dict):
            self.forms_data_versions.append(forms_data)

    def to_dict(self) -> Dict:
        return {
            self.url: {
                "emails": self.emails,
                "phonenumbers": self.phonenumbers,
                "keywordcount_versions": self.keywordcount_versions,
                "urls_with_text_versions": self.urls_with_text_versions,
                "forms_data_versions": self.forms_data_versions,
            }
        }
