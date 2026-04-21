import csv
import random
import pandas as pd
from collections import defaultdict
from collections import Counter
from urllib.parse import urlparse

# New method to process CSV using "Success" and "Not Found" statuses
def print_categorize_websites_by_status(input_file):
    successful_websites = []
    failed_websites = []
    websites = defaultdict(list)

    with open(input_file, mode='r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the header row
        for row in csv_reader:
            if len(row) >= 3:  # Ensure row has at least 3 columns (URL, Keyword, Status)
                url, keyword, status = row[:3]
                websites[url].append(status)

    for url, statuses in websites.items():
        if "Success" in statuses:
            successful_websites.append(url)
        else:
            failed_websites.append(url)

    print("Websites with 'Success' status")
    for website in successful_websites:
        print(website)
    print('-' * 30)
    print("Websites with 'Not Found' status")
    for website in failed_websites:
        print(website)
    print('-' * 20)
    print("Size of Websites with 'Success' status:", len(successful_websites))
    print("Size of Websites with 'Not Found' status:", len(failed_websites))

def get_missing_urls(input_file, url_list_file):
    websites = set()
    
    # Read URLs from the CSV file
    with open(input_file, mode='r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the header row
        for row in csv_reader:
            if len(row) >= 1:  # Ensure row has at least 1 column (URL)
                url = row[0]
                websites.add(url)
    
    # Read URLs from the text file
    with open(url_list_file, mode='r', encoding='utf-8') as file:
        all_urls = {line.strip() for line in file if line.strip()}
    
    # Find URLs present in the text file but missing from the CSV file
    missing_urls = all_urls - websites
    for url in missing_urls:
        print(url)

    print("Total missing URLs:", len(missing_urls))

def sort_csv_by_column(file_name, column_index):
    # Read the CSV and skip the header
    with open(file_name, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Skip header
        rows = list(reader)
    
    # Sort the rows by the specified column
    rows.sort(key=lambda row: row[column_index])

    # Rewrite the sorted data to the same file
    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write header back
        writer.writerows(rows)

    print(f"Sorted CSV by column {column_index} and saved to {file_name}")

def sort_csv_by_multiple_columns(file_name, column_indices):
    """
    Sort a CSV file by multiple columns in the given order.
    
    :param file_name: Name of the CSV file to sort
    :param column_indices: List of column indices to sort by (priority order)
    """
    # Read the CSV and skip the header
    with open(file_name, 'r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)  # Skip header
        rows = list(reader)
    
    # Sort the rows by the specified columns (order matters)
    rows.sort(key=lambda row: tuple(row[i] for i in column_indices))

    # Rewrite the sorted data to the same file
    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write header back
        writer.writerows(rows)

    print(f"Sorted CSV by columns {column_indices} and saved to {file_name}")

def get_random_urls_with_sources(csv_file, num_urls=50):
    # Load CSV
    df = pd.read_csv(csv_file)
    
    # Filter rows where 'Privacy Policy URL' is not 'N/A'
    valid_entries = df[df['Privacy Policy URL'] != ' N/A'][['URL', 'Privacy Policy URL']]
    
    # Convert to list of tuples (URL, Privacy Policy URL)
    valid_list = list(valid_entries.itertuples(index=False, name=None))
    
    # Get random 50 pairs (or all available if less than 50)
    return random.sample(valid_list, min(len(valid_list), num_urls))


def get_keyword_frequency(input_file):
    website_keywords = {}

    # Process the data
    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
    
        for row in reader:
            if len(row) < 2:
                continue  # Skip invalid rows

            website = row[0]
            keyword = row[1]
        
            # Normalize keyword if it's in "Full A-Tag Search: X" format
            if keyword.startswith("Full A-Tag Search:"):
                keyword = keyword.split(":")[1].strip().lower()

            if website not in website_keywords:
                website_keywords[website] = set()
            
            website_keywords[website].add(keyword.lower())

    # Count keyword occurrences across websites
    keyword_counts = Counter()
    for keywords in website_keywords.values():
        keyword_counts.update(keywords)

    # Get most frequent keywords
    most_common_keywords = keyword_counts.most_common()

    for keyword, count in most_common_keywords:
        print(f"{keyword}: {count}")

def get_privacy_policy_url_from_csv():
    df = pd.read_csv("results/data_source_with_ppurl.csv")  # Replace with your actual file name

    # Filter out N/A values from the 'Url' column
    urls = df["Privacy Policy URL"].dropna()

    # Write the URLs to a text file
    with open("urls1.txt", "w") as f:
        for url in urls:
            f.write(url + "\n")

    print("URLs extracted and saved to urls.txt")

def sort_text_file():
    with open("data/privacy_policy_urls.txt", "r") as f:
        urls = f.readlines()

    # Sort the URLs alphabetically
    urls = sorted(url.strip() for url in urls)

    # Write the sorted URLs back to the text file
    with open("urls.txt", "w") as f:
        for url in urls:
            f.write(url + "\n")

    print("URLs sorted and saved to urls.txt")

def check_for_domain_names():
    # Load CSV files
    csv1 = pd.read_csv("results/website_privacy_policy.csv")  # Replace with actual filename
    csv2 = pd.read_csv("results/data_source_with_ppurl.csv")  # Replace with actual filename

    # Extract domain names from 'Url' column in CSV1
    csv1['Extracted Domain'] = csv1['Url'].apply(lambda x: urlparse(x).netloc.replace("www.", ""))
    csv2['Extracted Domain'] = csv2['companyWebsite'].str.replace("www.", "", regex=False)

    # Count occurrences of each domain
    csv1_counts = csv1['Extracted Domain'].value_counts()
    csv2_counts = csv2['Extracted Domain'].value_counts()

    # Find domains where CSV2 count > CSV1 count
    extra_domains = csv2_counts[csv2_counts > csv1_counts.reindex(csv2_counts.index, fill_value=0)]

    # Print extra domains
    print("Domains appearing more in CSV2 than in CSV1:")
    print(extra_domains)


# Main function to execute the script
def main():

    sort_csv_by_column('results/url_presence_results.csv', 0)

    # sort_csv_by_multiple_columns('results/detailed_no_contact_results.csv', [0,1])

    # Example usage
    # random_urls = get_random_urls_with_sources("results/home_page_scrape_results.csv")
    # for url in random_urls:
    #     print(url)

    # print_categorize_websites_by_status('results/home_page_scrape_results.csv')

    # get_keyword_frequency("results/home_page_scrape_results.csv")

    # get_missing_urls('results/home_page_scrape_results.csv', "data/uchicago_website_list.txt")
    # get_privacy_policy_url_from_csv()
    # sort_text_file()

    # check_for_domain_names()


# Run the main function
if __name__ == "__main__":
    main()
