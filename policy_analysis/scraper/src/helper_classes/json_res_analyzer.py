import json
import csv
from collections import defaultdict

class JSONAnalyzer:
    def __init__(self, json_file):
        self.json_file = json_file
        self.data = self._load_json()
        self.url_keys = self._extract_keys()

    def _load_json(self):
        """Load JSON data from the file."""
        with open(self.json_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def get_email_status(self, privacy_policy_url):
        """Check if the given Privacy Policy URL has emails present in JSON data."""
        for obj in self.data:
            if privacy_policy_url in obj:
                policy_data = obj[privacy_policy_url]
                return bool(policy_data.get("emails"))  # True if emails exist, False otherwise
        return False  # If URL is not found in JSON
    
    def get_phonenumber_status(self, privacy_policy_url):
        """Check if the given Privacy Policy URL has phone numbers present in JSON data."""
        for obj in self.data:
            if privacy_policy_url in obj:
                policy_data = obj[privacy_policy_url]
                return bool(policy_data.get("phonenumbers"))  # True if phone numbers exist, False otherwise
        return False  # If URL is not found in JSON
    
    def _extract_keys(self):
        """Extract all privacy policy URLs from the JSON file."""
        return {list(obj.keys())[0] for obj in self.data if obj}  # Extract keys from JSON list of dicts

    def save_url_keys(self, output_txt_file):
        """Save extracted Privacy Policy URLs to a text file."""
        with open(output_txt_file, "w", encoding="utf-8") as file:
            for url in sorted(self.url_keys):  # Sorting for consistency
                file.write(url + "\n")
        print(f"Privacy Policy URLs saved to {output_txt_file}")

    def is_url_present(self, privacy_policy_url):
        """Check if the given Privacy Policy URL exists as a key in JSON data."""
        return privacy_policy_url in self.url_keys
    
def check_url_presence(csv_file, json_file, output_csv):
    analyzer = JSONAnalyzer(json_file)
    url_presence_data = []

    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            privacy_policy_url = row["Privacy Policy URL"]
            url_present = analyzer.is_url_present(privacy_policy_url)
            url_presence_data.append([privacy_policy_url, "Found" if url_present else "Not Found"])

    # Write output CSV
    with open(output_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Privacy Policy URL", "Status"])
        writer.writerows(url_presence_data)

    print(f"URL presence results saved to {output_csv}")

def process_contact_info(csv_file, json_file, email_output_csv, phonenumber_output_csv, no_contact_output_csv, 
                          detailed_email_csv, detailed_phone_csv, detailed_no_contact_csv):
    analyzer = JSONAnalyzer(json_file)
    
    email_counts = defaultdict(lambda: {"Email present": 0, "Email absent": 0, "Total": 0})
    phone_counts = defaultdict(lambda: {"Phone number present": 0, "Phone number absent": 0, "Total": 0})
    no_contact_counts = defaultdict(lambda: {"Neither present": 0, "Total": 0})

    email_data = []
    phone_data = []
    no_contact_data = []

    # Read CSV file and process data
    with open(csv_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            category = row["CCPA required"]
            privacy_policy_url = row["Privacy Policy URL"]
            company_website = row["companyWebsite"]
            url = row["url"]

            email_present = analyzer.get_email_status(privacy_policy_url)
            phonenumber_present = analyzer.get_phonenumber_status(privacy_policy_url)

            # Count emails
            email_counts[category]["Total"] += 1
            if email_present:
                email_counts[category]["Email present"] += 1
                email_data.append([category, "Email Found", company_website, url, privacy_policy_url])
            else:
                email_counts[category]["Email absent"] += 1
                email_data.append([category, "Email Not Found", company_website, url, privacy_policy_url])

            # Count phone numbers
            phone_counts[category]["Total"] += 1
            if phonenumber_present:
                phone_counts[category]["Phone number present"] += 1
                phone_data.append([category, "Phone Found", company_website, url, privacy_policy_url])
            else:
                phone_counts[category]["Phone number absent"] += 1
                phone_data.append([category, "Phone Not Found", company_website, url, privacy_policy_url])

            # Count sites with neither
            no_contact_counts[category]["Total"] += 1
            if not email_present and not phonenumber_present:
                no_contact_counts[category]["Neither present"] += 1
                no_contact_data.append([category, "Neither Found", company_website, url, privacy_policy_url])

    # Write detailed email results
    with open(detailed_email_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["CCPA required", "Status", "companyWebsite", "url", "Privacy Policy URL"])
        writer.writerows(email_data)

    # Write detailed phone number results
    with open(detailed_phone_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["CCPA required", "Status", "companyWebsite", "url", "Privacy Policy URL"])
        writer.writerows(phone_data)

    # Write detailed no contact results
    with open(detailed_no_contact_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["CCPA required", "Status", "companyWebsite", "url", "Privacy Policy URL"])
        writer.writerows(no_contact_data)

    print(f"Detailed email results saved to {detailed_email_csv}")
    print(f"Detailed phone results saved to {detailed_phone_csv}")
    print(f"Detailed no contact results saved to {detailed_no_contact_csv}")

    # Write email results
    with open(email_output_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Group Description", "Email present", "Email absent", "Total"])
        for category, counts in email_counts.items():
            writer.writerow([category, counts["Email present"], counts["Email absent"], counts["Total"]])

    # Write phone number results
    with open(phonenumber_output_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Group Description", "Phone number present", "Phone number absent", "Total"])
        for category, counts in phone_counts.items():
            writer.writerow([category, counts["Phone number present"], counts["Phone number absent"], counts["Total"]])

    # Write sites with neither emails nor phone numbers
    with open(no_contact_output_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Group Description", "Neither present", "Total"])
        for category, counts in no_contact_counts.items():
            writer.writerow([category, counts["Neither present"], counts["Total"]])

    print(f"Email results saved to {email_output_csv}")
    print(f"Phone results saved to {phonenumber_output_csv}")
    print(f"Sites with neither contact info saved to {no_contact_output_csv}")

if __name__ == "__main__":
    csv_file = "results/data_source_with_ppurl.csv"  # Replace with actual CSV file path
    json_file = "results/scraped_results.json"  # Replace with actual JSON file path

    email_output_csv = "results/email_category_results1.csv"
    phonenumber_output_csv = "results/phone_category_results1.csv"
    no_contact_output_csv = "results/no_contact_category_results1.csv"

    detailed_email_csv = "results/detailed_email_results.csv"
    detailed_phone_csv = "results/detailed_phone_results.csv"
    detailed_no_contact_csv = "results/detailed_no_contact_results.csv"


    analyzer = JSONAnalyzer("results/scraped_results.json")
    analyzer.save_url_keys("results/url_key1s.txt")

    # check_url_presence("results/data_source_with_ppurl.csv", "results/scraped_results.json", "results/url_presence_results1.csv")

    # process_contact_info(csv_file, json_file, email_output_csv, phonenumber_output_csv, no_contact_output_csv,
    #                       detailed_email_csv, detailed_phone_csv, detailed_no_contact_csv)