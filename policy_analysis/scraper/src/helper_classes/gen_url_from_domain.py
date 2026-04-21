import pandas as pd
import requests

def get_url(domain):
    domain = domain.lower()  # Convert to lowercase to standardize the domain format
    for scheme in ["https://", "http://"]:
        try:
            response = requests.get(scheme + domain, timeout=3)
            if response.status_code < 400:  # Valid response
                return scheme + domain
        except requests.RequestException:
            continue
    return "http://" + domain  # Fallback to HTTP if both fail

def main():
    # Read CSV file
    df = pd.read_csv("website_list.csv")
    
    print("Processing websites...")  # Progress monitoring
    
    # Get correct URLs
    df["url"] = df["website"].apply(lambda site: get_url(site))
    
    print("Finished processing websites. Saving to file...")  # Progress monitoring
    
    # Save to text file
    df["url"].to_csv("urls.txt", index=False, header=False)
    
    print("URLs saved to urls.txt")

if __name__ == "__main__":
    main()
