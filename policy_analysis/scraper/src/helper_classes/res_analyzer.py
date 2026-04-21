import json
import pandas as pd
from collections import defaultdict

def load_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def load_csv(csv_path):
    return pd.read_csv(csv_path)

def count_keys_with_identifiers(json_data, csv_data):
    categorized_identifiers_ccpa = defaultdict(lambda: {"Identifiers Present": 0, "Identifiers Not Found": 0, "Total": 0})
    
    for _, row in csv_data.iterrows():
        url = row["Privacy Policy URL"].strip()
        ccpa_category = row["CCPA required"].strip()
        
        for item in json_data:
            if url in item:
                value = item[url]
                has_identifier = False
                
                if "emails" in value and value["emails"]:
                    has_identifier = True
                if "phonenumbers" in value and value["phonenumbers"]:
                    has_identifier = True
                if "urls_with_text_versions" in value:
                    for url_dict in value["urls_with_text_versions"]:
                        if any(url_dict.values()):  # Check if any key has a non-empty value
                            has_identifier = True
                            break
                
                if has_identifier:
                    categorized_identifiers_ccpa[ccpa_category]["Identifiers Present"] += 1
                else:
                    categorized_identifiers_ccpa[ccpa_category]["Identifiers Not Found"] += 1
                
                categorized_identifiers_ccpa[ccpa_category]["Total"] += 1
    
    return categorized_identifiers_ccpa

def count_keys_with_two_identifiers(json_data, csv_data):
    categorized_two_identifiers_ccpa = defaultdict(lambda: {"Two Identifiers Present": 0, "Two Identifiers Not Found": 0, "Total": 0})
    categorized_two_identifiers_category = defaultdict(lambda: {"Two Identifiers Present": 0, "Two Identifiers Not Found": 0, "Total": 0})
    
    for _, row in csv_data.iterrows():
        url = row["Privacy Policy URL"].strip()
        ccpa_category = row["CCPA required"].strip()
        category = row["category"].strip()
        
        for item in json_data:
            if url in item:
                value = item[url]
                identifier_count = 0
                
                if "emails" in value and value["emails"]:
                    identifier_count += 1
                if "phonenumbers" in value and value["phonenumbers"]:
                    identifier_count += 1
                if "urls_with_text_versions" in value:
                    for url_dict in value["urls_with_text_versions"]:
                        if any(url_dict.values()):  # Check if any key has a non-empty value
                            identifier_count += 1
                            break
                
                if identifier_count >= 2:
                    categorized_two_identifiers_ccpa[ccpa_category]["Two Identifiers Present"] += 1
                    categorized_two_identifiers_category[(ccpa_category, category)]["Two Identifiers Present"] += 1
                else:
                    categorized_two_identifiers_ccpa[ccpa_category]["Two Identifiers Not Found"] += 1
                    categorized_two_identifiers_category[(ccpa_category, category)]["Two Identifiers Not Found"] += 1
                
                categorized_two_identifiers_ccpa[ccpa_category]["Total"] += 1
                categorized_two_identifiers_category[(ccpa_category, category)]["Total"] += 1
    
    return categorized_two_identifiers_ccpa, categorized_two_identifiers_category

def count_aggregated_presence(json_data):
    # Use sets to track unique emails and phone numbers
    unique_emails = set()
    unique_phone_numbers = set()
    
    # Counters for the final result
    aggregated_counts = {"Unique Emails Present": 0, "Unique Phone Numbers Present": 0}
    
    for item in json_data:
        for key, value in item.items():
            # Add emails to the unique set
            if "emails" in value and value["emails"]:
                for email in value["emails"]:
                    unique_emails.add(email)
            
            # Add phone numbers to the unique set
            if "phonenumbers" in value and value["phonenumbers"]:
                for phone in value["phonenumbers"]:
                    unique_phone_numbers.add(phone)
    
    # Update the counts with the size of each set
    aggregated_counts["Unique Emails Present"] = len(unique_emails)
    aggregated_counts["Unique Phone Numbers Present"] = len(unique_phone_numbers)
    
    return aggregated_counts, unique_emails, unique_phone_numbers

def categorize_nested_urls(json_data):
    # Categories to track
    valid_categories = [
        "Agents", "Right_To_Limit", "Opt_Out", "Right_To_Correct", 
        "Right_To_Know", "Generic_Request", "Right_To_Delete", "Manual", "Bypass"
    ]
    
    category_counts = {category: 0 for category in valid_categories}
    category_counts["Other"] = 0  # For URLs that don't match any category
    
    # URL to categories mapping to track which URLs belong to which categories
    url_categories = {}

    total_nested_urls = 0
    
    # Track unique URLs to avoid double counting
    unique_urls = set()
    
    for item in json_data:
        for key, value in item.items():
            if "urls_with_text_versions" in value:
                for url_dict in value["urls_with_text_versions"]:
                    for parent_url, nested_content in url_dict.items():
                        # Check if nested_content is a dictionary (URL → list mapping)
                        if isinstance(nested_content, dict):
                            for nested_url, items_list in nested_content.items():
                                total_nested_urls += 1
                                unique_urls.add(nested_url)
                                process_url_and_items(nested_url, items_list, valid_categories, category_counts, url_categories)
                        # Check if nested_content is a list of items directly
                        elif isinstance(nested_content, list):
                            process_url_and_items(parent_url, nested_content, valid_categories, category_counts, url_categories)
    print (len(unique_urls))
    return category_counts, url_categories

def process_url_and_items(url, items_list, valid_categories, category_counts, url_categories):
    """Process a URL and its associated items list"""
    # Track categories for this URL
    url_cats = set()
    has_manual_context = False
    
    # Check each item in the list for category
    for item_dict in items_list:
        if isinstance(item_dict, dict):  # Make sure it's a dictionary
            if "category" in item_dict and item_dict["category"] in valid_categories:
                url_cats.add(item_dict["category"])
            # Check for Manual context
            if "context" in item_dict and item_dict["context"] == "Manual":
                has_manual_context = True
    
    # If we found categories, add them
    if url_cats:
        for category in url_cats:
            category_counts[category] += 1
            
            if category not in url_categories:
                url_categories[category] = []
            url_categories[category].append(url)
    
    # If no categories but has Manual context, add to Manual
    elif has_manual_context:
        category_counts["Manual"] += 1
        
        if "Manual" not in url_categories:
            url_categories["Manual"] = []
        url_categories["Manual"].append(url)
    
    # If no categories and no Manual context, add to Other
    else:
        category_counts["Other"] += 1
        
        if "Other" not in url_categories:
            url_categories["Other"] = []
        url_categories["Other"].append(url)

def save_aggregated_results_to_csv(aggregated_counts, output_path):
    aggregated_df = pd.DataFrame([aggregated_counts])
    aggregated_df.to_csv(output_path.replace(".csv", "_aggregated_counts.csv"), index=False)

def count_presence_per_ccpa(json_data, csv_data):
    categorized_presence_ccpa = defaultdict(lambda: {"Emails Present": 0, "Phone Numbers Present": 0, "URLs Present": 0})
    
    for _, row in csv_data.iterrows():
        url = row["Privacy Policy URL"].strip()
        ccpa_category = row["CCPA required"].strip()
        
        for item in json_data:
            if url in item:
                value = item[url]
                
                if "emails" in value and value["emails"]:
                    categorized_presence_ccpa[ccpa_category]["Emails Present"] += 1
                if "phonenumbers" in value and value["phonenumbers"]:
                    categorized_presence_ccpa[ccpa_category]["Phone Numbers Present"] += 1
                if "urls_with_text_versions" in value:
                    for url_dict in value["urls_with_text_versions"]:
                        if any(url_dict.values()):
                            categorized_presence_ccpa[ccpa_category]["URLs Present"] += 1
                            break
    
    return categorized_presence_ccpa

def count_presence_per_ccpa_category(json_data, csv_data):
    categorized_presence_category = defaultdict(lambda: {"Emails Present": 0, "Phone Numbers Present": 0, "URLs Present": 0})
    
    for _, row in csv_data.iterrows():
        url = row["Privacy Policy URL"].strip()
        ccpa_category = row["CCPA required"].strip()
        category = row["category"].strip()
        
        for item in json_data:
            if url in item:
                value = item[url]
                
                if "emails" in value and value["emails"]:
                    categorized_presence_category[(ccpa_category, category)]["Emails Present"] += 1
                if "phonenumbers" in value and value["phonenumbers"]:
                    categorized_presence_category[(ccpa_category, category)]["Phone Numbers Present"] += 1
                if "urls_with_text_versions" in value:
                    for url_dict in value["urls_with_text_versions"]:
                        if any(url_dict.values()):
                            categorized_presence_category[(ccpa_category, category)]["URLs Present"] += 1
                            break
    
    return categorized_presence_category

def save_results_to_csv(categorized_presence_ccpa, categorized_presence_category, output_path):
    presence_ccpa_data = [(ccpa, data["Emails Present"], data["Phone Numbers Present"], data["URLs Present"]) 
                           for ccpa, data in categorized_presence_ccpa.items()]
    presence_ccpa_df = pd.DataFrame(presence_ccpa_data, columns=["CCPA required", "Emails Present", "Phone Numbers Present", "URLs Present"])
    
    presence_category_data = [(ccpa, category, data["Emails Present"], data["Phone Numbers Present"], data["URLs Present"]) 
                              for (ccpa, category), data in categorized_presence_category.items()]
    presence_category_df = pd.DataFrame(presence_category_data, columns=["CCPA required", "Category", "Emails Present", "Phone Numbers Present", "URLs Present"])
    
    presence_ccpa_df.to_csv(output_path.replace(".csv", "_presence_ccpa.csv"), index=False)
    presence_category_df.to_csv(output_path.replace(".csv", "_presence_category.csv"), index=False)

def main(json_path, csv_path, output_path):
    json_data = load_json(json_path)
    csv_data = load_csv(csv_path)
    
    # categorized_presence_ccpa = count_presence_per_ccpa(json_data, csv_data)
    # categorized_presence_category = count_presence_per_ccpa_category(json_data, csv_data)
    # save_results_to_csv(categorized_presence_ccpa, categorized_presence_category, output_path)
    
    # print(f"Results saved to {output_path.replace('.csv', '_presence_ccpa.csv')} and {output_path.replace('.csv', '_presence_category.csv')}")

    # categorized_identifiers_ccpa = count_keys_with_identifiers(json_data, csv_data)
    aggregated_counts = count_aggregated_presence(json_data)
    
    save_aggregated_results_to_csv(aggregated_counts, output_path)
    # print(f"Aggregated results saved to {output_path.replace('.csv', '_aggregated_counts.csv')}")

    # category_counts, url_by_category = categorize_nested_urls(json_data)

    # print("Category counts:")
    # for category, count in category_counts.items():
    #     if count > 0:
    #         print(f"  {category}: {count}")

# Example Usage
main("results/scraped_results.json", "results/data_source_with_ppurl.csv", "output1.csv")
