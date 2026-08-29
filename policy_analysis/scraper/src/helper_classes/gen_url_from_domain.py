# Convert to lowercase to standardize the domain format
import pandas as pd
import requests

def get_url(domain):
    domain = domain.lower()
    for scheme in ["https://", "http://"]:
        try:
            response = requests.get(scheme + domain, timeout=3)
            if response.status_code < 400:
                return scheme + domain
        except requests.RequestException:
            continue
    return "http://" + domain

def main():

    df = pd.read_csv("website_list.csv")

    print("Processing websites...")

    df["url"] = df["website"].apply(lambda site: get_url(site))

    print("Finished processing websites. Saving to file...")

    df["url"].to_csv("urls.txt", index=False, header=False)

    print("URLs saved to urls.txt")

if __name__ == "__main__":
    main()
