import pandas as pd
import json
import os
import sys
import signal

# Load config.json
with open("cookie_categorization/config.json", "r") as config_file:
    config = json.load(config_file)

# Extract file paths from config
INPUT_FILES = config["file_paths"]["input_files"]
MY_COOKIE_DB = config["file_paths"]["my_cookie_db"]
OPEN_COOKIE_DB = config["file_paths"]["open_cookie_db"]
COOKIE_CUTTER_DB = config["file_paths"]["cookie_cutter_db"]
COOKIES_TO_FETCH = config["file_paths"]["cookies_to_fetch"]
FAILED_COOKIES_FILE = config["file_paths"]["failed_cookies"]
OUTPUT_DIR = config["file_paths"]["output_directory"]

# Ensure the output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Register Signal Handler to Save on Interruption
def save_progress_and_exit(signum, frame):
    print("\n[WARNING] Script interrupted! Saving progress before exit...")
    output_file = os.path.join(OUTPUT_DIR, "processed_" + os.path.basename(INPUT_FILES[0]))
    results_df.to_csv(output_file, index=False)
    print(f"[INFO] Partial progress saved to {output_file}. Exiting.")
    sys.exit(1)

signal.signal(signal.SIGINT, save_progress_and_exit)
signal.signal(signal.SIGTERM, save_progress_and_exit)

# Load input CSV
print(f"[INFO] Processing input file: {INPUT_FILES[0]}")

if os.path.exists(INPUT_FILES[0]):
    results_df = pd.read_csv(INPUT_FILES[0], dtype=str, on_bad_lines="skip")
else:
    print("[ERROR] Input file not found. Exiting.")
    sys.exit(1)

# Load `mycookiebase.csv`
if os.path.exists(MY_COOKIE_DB):
    mycookie_df = pd.read_csv(MY_COOKIE_DB, dtype=str)
    mycookie_df["cookie_name"] = mycookie_df["cookie_name"].str.lower().str.strip()
    mycookie_df = mycookie_df.drop_duplicates(subset="cookie_name", keep="first")
    mycookie_dict = mycookie_df.set_index("cookie_name")[["category", "description"]].to_dict(orient="index")
    print(f"[INFO] Loaded {len(mycookie_dict)} cookies from mycookiebase.csv")
else:
    print("[WARNING] `mycookiebase.csv` missing. Creating an empty dictionary.")
    mycookie_dict = {}

# Load `open-cookie-database.csv`
if os.path.exists(OPEN_COOKIE_DB):
    open_cookie_df = pd.read_csv(OPEN_COOKIE_DB, dtype=str)
    open_cookie_df.rename(columns={"Cookie / Data Key name": "cookie_name"}, inplace=True)
    open_cookie_df.drop_duplicates(subset="cookie_name", keep="first", inplace=True)
    open_cookie_dict = open_cookie_df.set_index("cookie_name")[["category", "description"]].to_dict(orient="index")

    # Wildcard Matching List
    if "Wildcard" in open_cookie_df.columns:
        open_cookie_df["Wildcard"] = open_cookie_df["Wildcard"].astype(str).map(
            {"1": True, "0": False, "TRUE": True, "FALSE": False}
        )
        wildcard_entries = open_cookie_df[open_cookie_df["Wildcard"] == True][["cookie_name", "category", "description"]].values.tolist()
    else:
        wildcard_entries = []  # Ensure wildcard_entries is always initialized

else:
    print("[WARNING] `open-cookie-database.csv` missing.")
    open_cookie_dict = {}
    wildcard_entries = []  # Fix: Ensure wildcard_entries is defined

# Load `cookie_cutter_db.json`
if os.path.exists(COOKIE_CUTTER_DB):
    with open(COOKIE_CUTTER_DB, "r") as f:
        cookie_cutter_dict = json.load(f)
    print(f"[INFO] Loaded {len(cookie_cutter_dict)} entries from cookie_cutter_db.json")
else:
    print("[WARNING] `cookie_cutter_db.json` missing.")
    cookie_cutter_dict = {}

# Load `failed_cookies.json`
if os.path.exists(FAILED_COOKIES_FILE):
    with open(FAILED_COOKIES_FILE, "r") as f:
        failed_cookies = set(json.load(f))
    print(f"[INFO] Loaded {len(failed_cookies)} failed cookies.")
else:
    failed_cookies = set()

# Prepare list of cookies to fetch
cookies_to_fetch = []

def find_category_description(cookie_name):
    if pd.isna(cookie_name) or not isinstance(cookie_name, str):
        return "", ""

    cookie_name = str(cookie_name).lower().strip()

    # 1. Check mycookiebase.csv
    if cookie_name in mycookie_dict:
        category, description = mycookie_dict[cookie_name]["category"], mycookie_dict[cookie_name]["description"]
        if category and description:
            return category, description
        if category:
            return category, description
        if description:
            return category, description

    # 2. Check open-cookie-database.csv
    if cookie_name in open_cookie_dict:
        return open_cookie_dict[cookie_name]["category"], open_cookie_dict[cookie_name]["description"]

    # 3. Check Wildcard Matches
    for wildcard_name, category, description in wildcard_entries:
        if cookie_name.startswith(wildcard_name):
            return category, description

    # 4. Check cookie_cutter_db.json
    if cookie_name in cookie_cutter_dict:
        return cookie_cutter_dict[cookie_name], ""

    # 5. Check failed_cookies.json
    if cookie_name in failed_cookies:
        return "", ""

    # 6. Cookie Needs Fetching
    cookies_to_fetch.append(cookie_name)
    return "", ""

# Process rows in batches
BATCH_SIZE = 50
for start in range(0, len(results_df), BATCH_SIZE):
    batch_df = results_df.iloc[start:start + BATCH_SIZE]
    updated_cookies = []

    for idx, row in batch_df.iterrows():
        cookie = row["cookie_name"]

        if pd.notna(row.get("category")) and row["category"].strip():
            continue  
        if pd.notna(row.get("description")) and row["description"].strip():
            continue  

        category, description = find_category_description(cookie)

        if category or description:
            results_df.at[idx, "category"] = category
            results_df.at[idx, "description"] = description
            updated_cookies.append(f"{cookie} → {category} | {description}")

    output_file = os.path.join(OUTPUT_DIR, "processed_" + os.path.basename(INPUT_FILES[0]))
    results_df.to_csv(output_file, index=False)
    print(f"[INFO] Processed {start + BATCH_SIZE} rows. Updated {len(updated_cookies)} missing cookies.")

    if updated_cookies:
        print("[UPDATED COOKIES]")
        for item in updated_cookies:
            print(f"  - {item}")

# Save `cookies_to_fetch.json`
with open(COOKIES_TO_FETCH, "w") as f:
    json.dump(cookies_to_fetch, f)

print(f"[INFO] {len(cookies_to_fetch)} cookies need fetching. Run `cookiepedia.js` to fetch them.")