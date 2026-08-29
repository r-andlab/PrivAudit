# New method to process CSV using "Success" and "Not Found" statuses
import csv
import random
import pandas as pd
from collections import defaultdict
from collections import Counter
from urllib.parse import urlparse

def print_categorize_websites_by_status(input_file):
    successful_websites = []
    failed_websites = []
    websites = defaultdict(list)

    with open(input_file, mode='r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)
        for row in csv_reader:
            if len(row) >= 3:
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

    with open(input_file, mode='r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)
        for row in csv_reader:
            if len(row) >= 1:
                url = row[0]
                websites.add(url)

    with open(url_list_file, mode='r', encoding='utf-8') as file:
        all_urls = {line.strip() for line in file if line.strip()}

    missing_urls = all_urls - websites
    for url in missing_urls:
        print(url)

    print("Total missing URLs:", len(missing_urls))

def sort_csv_by_column(file_name, column_index):

    with open(file_name, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)
        rows = list(reader)

    rows.sort(key=lambda row: row[column_index])

    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Sorted CSV by column {column_index} and saved to {file_name}")

def sort_csv_by_multiple_columns(file_name, column_indices):

    with open(file_name, 'r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)
        rows = list(reader)

    rows.sort(key=lambda row: tuple(row[i] for i in column_indices))

    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Sorted CSV by columns {column_indices} and saved to {file_name}")

def get_random_urls_with_sources(csv_file, num_urls=50):

    df = pd.read_csv(csv_file)

    valid_entries = df[df['Privacy Policy URL'] != ' N/A'][['URL', 'Privacy Policy URL']]

    valid_list = list(valid_entries.itertuples(index=False, name=None))

    return random.sample(valid_list, min(len(valid_list), num_urls))

def get_keyword_frequency(input_file):
    website_keywords = {}

    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            if len(row) < 2:
                continue

            website = row[0]
            keyword = row[1]

            if keyword.startswith("Full A-Tag Search:"):
                keyword = keyword.split(":")[1].strip().lower()

            if website not in website_keywords:
                website_keywords[website] = set()

            website_keywords[website].add(keyword.lower())

    keyword_counts = Counter()
    for keywords in website_keywords.values():
        keyword_counts.update(keywords)

    most_common_keywords = keyword_counts.most_common()

    for keyword, count in most_common_keywords:
        print(f"{keyword}: {count}")

def get_privacy_policy_url_from_csv():
    df = pd.read_csv("results/data_source_with_ppurl.csv")

    urls = df["Privacy Policy URL"].dropna()

    with open("urls1.txt", "w") as f:
        for url in urls:
            f.write(url + "\n")

    print("URLs extracted and saved to urls.txt")

def sort_text_file():
    with open("data/privacy_policy_urls.txt", "r") as f:
        urls = f.readlines()

    urls = sorted(url.strip() for url in urls)

    with open("urls.txt", "w") as f:
        for url in urls:
            f.write(url + "\n")

    print("URLs sorted and saved to urls.txt")

def check_for_domain_names():

    csv1 = pd.read_csv("results/website_privacy_policy.csv")
    csv2 = pd.read_csv("results/data_source_with_ppurl.csv")

    csv1['Extracted Domain'] = csv1['Url'].apply(lambda x: urlparse(x).netloc.replace("www.", ""))
    csv2['Extracted Domain'] = csv2['companyWebsite'].str.replace("www.", "", regex=False)

    csv1_counts = csv1['Extracted Domain'].value_counts()
    csv2_counts = csv2['Extracted Domain'].value_counts()

    extra_domains = csv2_counts[csv2_counts > csv1_counts.reindex(csv2_counts.index, fill_value=0)]

    print("Domains appearing more in CSV2 than in CSV1:")
    print(extra_domains)

def main():

    sort_csv_by_column('results/url_presence_results.csv', 0)

if __name__ == "__main__":
    main()
