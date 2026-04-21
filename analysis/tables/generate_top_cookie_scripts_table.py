#!/usr/bin/env python3
"""Generate table of top third-party scripts setting first-party targeting cookies."""

import pandas as pd
import numpy as np

# Load reclassified dataset
df = pd.read_csv('../Analysis/final_default_state_comprehensive_reclassified.csv', dtype=str, low_memory=False)

print(f'Loaded {len(df)} records from {df["website"].nunique()} websites')

# Helper functions
def has_value(val):
    if pd.isna(val):
        return False
    val_str = str(val).strip().lower()
    return val_str not in ['', 'nan', 'none', 'null']

def norm_category(val: str) -> str:
    if not isinstance(val, str):
        return 'Unknown'
    key = val.strip().lower()
    if key in ['targeting', 'advertisement']:
        return 'Targeting'
    elif key == 'performance':
        return 'Performance'
    elif key == 'functional':
        return 'Functional'
    elif key in ['strictly necessary', 'necessary']:
        return 'Necessary'
    else:
        return 'Unknown'

def is_third_party(val):
    if not isinstance(val, str):
        return False
    return val.strip().lower() in ['yes', 'true', '1']

# Normalize columns
df['Cookie_Type'] = df['category'].apply(norm_category)
df['is_3p_script'] = df['script_is_third_party'].apply(is_third_party)

# Filter to:
# 1. Targeting cookies only
# 2. Set by third-party scripts
# 3. In default state (initial_cookies)
targeting = df[df['Cookie_Type'] == 'Targeting'].copy()
targeting_3p_scripts = targeting[targeting['is_3p_script']].copy()
targeting_3p_default = targeting_3p_scripts[targeting_3p_scripts['initial_cookies'].apply(has_value)].copy()

print(f'\nFiltered to {len(targeting_3p_default)} targeting cookies set by 3P scripts in default state')
print(f'From {targeting_3p_default["website"].nunique()} websites')

# Use set_by_script_domain column
script_col = 'set_by_script_domain'
print(f'\nUsing column: {script_col}')

# Clean up script domains
def clean_domain(val):
    if not isinstance(val, str):
        return 'Unknown'
    val = val.strip()
    return val if val else 'Unknown'

targeting_3p_default['script_domain'] = targeting_3p_default[script_col].apply(clean_domain)

# Remove 'Unknown' scripts
targeting_3p_default = targeting_3p_default[targeting_3p_default['script_domain'] != 'Unknown'].copy()

print(f'After filtering unknown domains: {len(targeting_3p_default)} cookies')

# Group by script domain
script_stats = (
    targeting_3p_default.groupby('script_domain')
    .agg({
        'cookie_name': 'count',  # number of cookies
        'website': 'nunique'      # number of websites
    })
    .rename(columns={'cookie_name': 'cookies', 'website': 'websites'})
    .sort_values('cookies', ascending=False)
)

# Calculate percentage of sample websites
total_websites = df['website'].nunique()
script_stats['pct_sample'] = (script_stats['websites'] / total_websites) * 100

# Get top 10
top_10 = script_stats.head(10).copy()

# Calculate total targeting cookies from 3P scripts
total_targeting_3p = len(targeting_3p_default)

# Calculate cumulative percentage covered by top 10
top_10_cookies = top_10['cookies'].sum()
top_10_pct = (top_10_cookies / total_targeting_3p) * 100

print(f'\n' + '='*80)
print(f'Top 10 Third-Party Scripts Setting Targeting Cookies (Default State)')
print('='*80)
print(f'\nTotal targeting cookies from 3P scripts: {total_targeting_3p:,}')
print(f'Top 10 cover: {top_10_cookies:,} cookies ({top_10_pct:.1f}%)')
print(f'\nTop 10 breakdown:')
print(top_10.to_string())

# Manual categorization of script domains (based on known services)
script_categories = {
    'www.googletagmanager.com': 'Tag Management',
    'securepubads.g.doubleclick.net': 'Advertising',
    'bat.bing.com': 'Advertising / Analytics',
    'analytics.tiktok.com': 'Social / Analytics',
    'ak.sail-horizon.com': 'Marketing Automation',
    'assets.adobedtm.com': 'Tag Management',
    'connect.facebook.net': 'Social / Ads',
    'tags.tiqcdn.com': 'Tag Mgmt. (Tealium)',
    'cdn.attn.tv': 'Marketing Platform',
    'sc-static.net': 'Audience Measurement',
    'www.google-analytics.com': 'Analytics',
    'static.ads-twitter.com': 'Social / Ads',
    'cdn.segment.com': 'Analytics Platform',
    'snap.licdn.com': 'Social / Ads',
    'px.ads.linkedin.com': 'Social / Ads',
    'www.clarity.ms': 'Analytics',
    't.co': 'Social / Ads',
    'cdn.cookielaw.org': 'Consent Management',
    'tr.snapchat.com': 'Social / Ads',
}

# Generate LaTeX table
latex_lines = []
latex_lines.append(r'  \begin{table*}[!t]')
latex_lines.append(r'  \centering')
latex_lines.append(rf'  \caption{{Top 10 third-party scripts responsible for setting first-party targeting cookies. Combined, these account for {top_10_pct:.1f}\% of such cookies.}}')
latex_lines.append(r'  \label{tab:top-cookie-scripts}')
latex_lines.append(r'  \footnotesize')
latex_lines.append(r'  \begin{tabular}{p{3.3cm}|p{1.2cm}|p{1.2cm}|p{1.5cm}|p{3.5cm}}')
latex_lines.append(r'  \toprule')
latex_lines.append(r'  \textbf{Script Domain} & \textbf{Cookies} & \textbf{Websites} & \textbf{\% of Sample} & \textbf{Category} \\')
latex_lines.append(r'  \midrule')

for i, (domain, row) in enumerate(top_10.iterrows()):
    cookies = int(row['cookies'])
    websites = int(row['websites'])
    pct_sample = row['pct_sample']
    category = script_categories.get(domain, 'Unknown Service')
    
    # Alternate gray rows
    if i % 2 == 0:
        prefix = r'  \cellcolor{gray!20}'
    else:
        prefix = r'  '
    
    line = f'{prefix}{domain}\n      & {cookies} & {websites} & '
    line += rf'\gradientcell{{{pct_sample:.1f}}}{{0}}{{60}}{{red}}{{green}}{{40}}\% & {category} \\'
    
    latex_lines.append(line)

latex_lines.append(r'  \bottomrule')
latex_lines.append(r'  \end{tabular}')
latex_lines.append(r'  \end{table*}')

latex_output = '\n'.join(latex_lines)

# Save to file
output_file = 'table_top_cookie_scripts_updated.tex'
with open(output_file, 'w') as f:
    f.write(latex_output)

print(f'\n[OK] LaTeX table saved to: {output_file}')
print('\n' + '='*80)
print('Generated LaTeX Table:')
print('='*80)
print(latex_output)
