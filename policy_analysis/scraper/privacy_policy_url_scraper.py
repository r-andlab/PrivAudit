# Standard library imports
import os
import csv
from typing import Optional
from src.utils import Logger, WebDriverManager
from src.timeout import TimeoutHandler
from src.timeout import TimeoutException
from src.processors import PageLoader

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Config:

    FILES = {
        'input_file': "data/url_list_to_process.txt",
        'results_csv': "results/home_page_scrape_results.csv",
        'output_file': "data/privacy_policy_urls.txt"
    }

    KEYWORDS = {
        'privacy': [
            "Privacy Policy", "Privacy","Your Privacy Rights"
        ],
        'href': ["privacy"]
    }

    TIMEOUT_SECONDS = {
        'a_tag_search': 90,
        'load_scroll_time' : 90
    }
    TIMEOUT_SECONDS['element_search'] = sum(TIMEOUT_SECONDS.values())

class FileManager:

    @staticmethod
    def cleanup_directories() -> None:
        Logger.log("Starting cleanup of directories...")
        if os.path.exists(Config.FILES['results_csv']):
            os.remove(Config.FILES['results_csv'])
            Logger.log(f"Deleted existing CSV file: {Config.FILES['results_csv']}")

        output_dir = os.path.dirname(Config.FILES['output_file'])
        os.makedirs(output_dir, exist_ok=True)
        open(Config.FILES['output_file'], 'w').close()
        Logger.log(f"Create output file at: {Config.FILES['output_file']}")

class PrivacyPolicyScraper:

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.page_loader = PageLoader(driver)
        self.file_manager = FileManager()

    def cleanup(self) -> None:
        if self.driver:
            Logger.log("Closing WebDriver...")
            self.driver.quit()
            Logger.log("WebDriver closed.")

    @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['element_search'], "Privacy policy search")
    def find_privacy_policy(self, website_url: str) -> Optional[tuple]:
        try:
            Logger.log(f"Processing website: {website_url}")

            if not self.page_loader.load_url(website_url):
                Logger.log(f"Skipping {website_url} due to failed initial load")
                return None

            try:
                self.page_loader.attempt_page_load()
            except TimeoutException as e:
                Logger.log(f"Timeout while waiting for the page to load {website_url}: {str(e)}")

            try:
                self.page_loader.attempt_scroll()
            except TimeoutException as e:
                Logger.log(f"Timeout while scrolling through the page {website_url}: {str(e)}")

            for keyword in Config.KEYWORDS['privacy']:
                try:
                    Logger.log(f"Searching for keyword: {keyword}")
                    elements = self.driver.find_elements(
                        By.XPATH,
                        f"//a[@href and contains(normalize-space(text()), '{keyword}')] | "
                        f"//a[@href and .//span[contains(normalize-space(text()), '{keyword}')]]"
                    )

                    for element in elements:
                        href = element.get_attribute("href")
                        if href:
                            Logger.log(f"Found privacy policy link with priority keyword '{keyword}': {href}")
                            return (keyword, href)
                except Exception as e:
                    Logger.log(f"Error while searching for keyword '{keyword}': {e}")
                    continue

            Logger.log("XPath search yielded no results, falling back to full <a> tag search...")
            result = self._search_a_tags()
            if result:
                return result

            return None
        except TimeoutException as e:
            Logger.log(f"Timeout while processing {website_url}: {str(e)}")
            return None
        except Exception as e:
            Logger.log(f"Error processing {website_url}: {str(e)}")
            return None

    @TimeoutHandler.with_timeout(Config.TIMEOUT_SECONDS['a_tag_search'], "Anchor tag search")
    def _search_a_tags(self) -> Optional[tuple]:
        Logger.log("Performing direct <a> tag search...")
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            privacy_keywords = [keyword.lower() for keyword in Config.KEYWORDS['privacy']]
            link_matches = {}

            for link in self.driver.find_elements(By.TAG_NAME, "a"):
                try:
                    link_text = link.text.strip().lower()
                    href = link.get_attribute('href')
                    if not href:
                        continue

                    href = href.strip().lower()

                    for i, keyword in enumerate(privacy_keywords):
                        if keyword in link_text:

                            if i not in link_matches:
                                link_matches[i] = (f"Text Match: {keyword}", href)
                                break

                    if not any(p <= len(privacy_keywords) for p in link_matches.keys()):
                        for i, href_keyword in enumerate(Config.KEYWORDS['href']):
                            href_keyword = href_keyword.lower()
                            if href_keyword in href:

                                priority_index = len(privacy_keywords) + i
                                if priority_index not in link_matches:
                                    link_matches[priority_index] = (f"URL Match: {href_keyword}", href)
                                    break

                except Exception as e:
                    Logger.log(f"Error processing <a> tag: {str(e)}")
                    continue

            if link_matches:
                highest_priority = min(link_matches.keys())
                keyword, href = link_matches[highest_priority]
                Logger.log(f"Found privacy policy URL: {href} (matched: {keyword})")
                return (keyword, href)

            return None

        except TimeoutException as e:
            Logger.log(f"Timeout while searching <a> tags: {str(e)}")
            return None
        except Exception as e:
            Logger.log(f"Error searching <a> tags: {str(e)}")
            return None

def main():

    driver = None
    try:

        FileManager.cleanup_directories()
        driver = WebDriverManager.create_driver()
        scraper = PrivacyPolicyScraper(driver)

        with open(Config.FILES['input_file'], 'r') as infile, \
             open(Config.FILES['output_file'], 'w') as outfile, \
             open(Config.FILES['results_csv'], 'w', newline='', encoding='utf-8') as csvfile:

            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(["URL", "Keyword", "Status", "Privacy Policy URL"])

            for line in infile:
                try:
                    website_url = line.strip()
                    result = None

                    try:
                        result = scraper.find_privacy_policy(website_url)
                    except TimeoutException as e:
                        Logger.log(f"Timeout while processing {website_url}: {str(e)}")

                    if result:
                        keyword, privacy_url = result
                        outfile.write(f"{privacy_url}\n")
                        csv_writer.writerow([website_url, keyword, "Success", privacy_url])
                    else:
                        csv_writer.writerow([website_url, "N/A", "Not Found", ""])
                except Exception as e:
                        Logger.log(f"Error processing url - {website_url}: {str(e)}")
                        continue
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()
