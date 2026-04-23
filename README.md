# PrivAudit: A Dual-Lens Auditing Framework for Website Privacy Practices under the CCPA

## Overview

PrivAudit audits website privacy practices under the CCPA by combining two modules:

1. **Privacy Policy Analysis** — Scrapes privacy policies and evaluates them against a CCPA-specific rubric using an LLM pipeline.
2. **Browser-Based Cookie Analysis** — Crawls websites under six privacy configurations and records all cookies, including script-based third-party attribution.

## Repository Structure

```
PrivAudit/
├── crawler/                     # Puppeteer-based cookie crawler
│   ├── scripts/                 # Main crawler + GPC collection scripts
│   ├── configs/                 # Browser profile configurations
│   ├── flows/                   # Per-website cookie banner selectors
│   ├── gpc_toolkit/             # GPC shell runners + data merge scripts
│   └── package.json
├── policy_analysis/             # Privacy policy pipeline
│   ├── scraper/                 # Selenium-based policy text scraper
│   ├── extract_policy_claims.ipynb  # LLM analysis notebook
│   ├── calculate_significance.py
│   └── prompts/                 # CCPA rubric prompt
├── cookie_categorization/       # Cookie classification
│   ├── update_cookies.py        # Multi-source categorization pipeline
│   ├── cookie_categorization.py # Category standardization
│   └── cookiepedia.js           # Cookiepedia API scraper
├── banner_detection/            # Consent banner detector
├── analysis/
│   ├── tables/                  # 6 table generators
│   └── figures/                 # 3 figure generators
├── data/
│   └── data.zip                 # All datasets (see Data section)
├── requirements.txt
└── .gitignore
```

## Data

All datasets are available in `data/data.zip`. Unzip before running analysis scripts:

```bash
cd data && unzip data.zip -d ../Analysis
```

## Installation

```bash
git clone [this-repo-url]
cd PrivAudit

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node.js (for crawler)
cd crawler && npm install && cd ..

# Unzip data
cd data && unzip data.zip -d ../Analysis && cd ..
```

**Requirements:** Python >= 3.10, Node.js >= 18.x, Google Chrome.

## Usage

### Cookie Crawler

```bash
cd crawler/scripts
node cookie_profile_test.js --config ../configs/config.json
```

Crawls each website under six configurations: Default, Block Third-Party, DNT, GPC, uBlock Origin, and Consent-O-Matic.

### Privacy Policy Scraper

```bash
cd policy_analysis/scraper
python3 privacy_policy_url_scraper.py    # Find policy URLs
python3 privacy_policy_data_scraper.py   # Extract policy text
```

Produces `scraped_results.json`, which feeds into the LLM notebook.

### LLM Policy Analysis

```bash
export OPENAI_API_KEY="sk-..."
cd policy_analysis
jupyter notebook extract_policy_claims.ipynb
```

### Reproducing Tables and Figures

```bash
# Tables
cd analysis/tables
cp ../Analysis/data_source.csv .
cp ../Analysis/ccpa_policy_audit_data_source_mapped.json .
python3 generate_top_cookie_scripts_table.py
python3 generate_cookie_setter_table.py
python3 generate_ccpa_attribution_table_new.py
python3 generate_cookie_attributes_table.py
python3 generate_accessible_websites_table.py
python3 generate_updated_policy_table_final.py

# Figures
cd ../figures
python3 plot_split_violin_updated.py
python3 plot_cdf_comprehensive_banner_ccpa.py
python3 plot_ecdf_lifespan_ccpa_split.py
```

## Cookie Categorization Databases

The cookie categorization pipeline (`cookie_categorization/`) requires external databases that are not included in this repository due to licensing. Download them from their original sources and place them in `cookie_categorization/databases/`:

| Database | Source |
|---|---|
| Open Cookie Database | https://github.com/jkwakman/Open-Cookie-Database |
| Cookiepedia | https://cookiepedia.co.uk |
| Cookie Cutter DB | https://github.com/nickcounts/CookieCutter |
| DuckDuckGo Tracker Radar | https://github.com/nickcounts/tracker-radar |
| Disconnect Tracking Lists | https://github.com/nickcounts/disconnect-tracking-protection |

## Ethical Considerations

All crawling was conducted from California. PrivAudit makes fewer than 10 requests per website. No user data was collected beyond publicly available website responses.

## Citation

```
[Paper citation will be added upon acceptance]
```
