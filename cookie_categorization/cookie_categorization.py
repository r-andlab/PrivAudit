# Remove special characters
import pandas as pd
import re

def standardize_category(category):
    category = category.lower().strip().replace('"', '')
    category = re.sub(r'[^a-zA-Z0-9 ]', '', category)

    category_mapping = {
        "Strictly Necessary Cookies": ["necessary", "essential", "required", "mandatory", "security"],
        "Functional Cookies": ["functional", "preference", "preferences", "social media", "support"],
        "Performance Cookies": ["performance", "analytics", "statistics", "measurement", "load balancing"],
        "Targeting Cookies": ["targeting", "advertising", "marketing", "tracking", "profiling", "personalization"]
    }

    for standard_category, keywords in category_mapping.items():
        if any(keyword in category for keyword in keywords):
            return standard_category

    return "Other"

def clean_cookie_data(input_file):
    df = pd.read_csv(input_file)

    if 'category' not in df.columns:
        raise ValueError("The input file does not contain a 'category' column.")

    df['category_cleaned'] = df['category'].astype(str).apply(standardize_category)

    output_file = input_file.replace('.csv', '_cleaned.csv')
    df.to_csv(output_file, index=False)
    print(f"Cleaned file saved as: {output_file}")

input_file = input("Enter the filename (with path if needed): ")
clean_cookie_data(input_file)
