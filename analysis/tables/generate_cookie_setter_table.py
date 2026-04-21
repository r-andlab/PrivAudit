#!/usr/bin/env python3
"""Generate cookie setter breakdown table with reclassified data."""

import pandas as pd

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

# Filter to Default state
df['Cookie_Type'] = df['category'].apply(norm_category)
df['is_3p'] = df['script_is_third_party'].apply(is_third_party)
default_df = df[df['initial_cookies'].apply(has_value)].copy()

print(f'Default state cookies: {len(default_df)}')

# Calculate statistics
cookie_types = ['Targeting', 'Performance', 'Functional', 'Necessary', 'Unknown']
results = {}

for cookie_type in cookie_types:
    type_df = default_df[default_df['Cookie_Type'] == cookie_type]
    total = len(type_df)
    third_party = type_df['is_3p'].sum()
    third_party_pct = (third_party / total * 100) if total > 0 else 0.0
    
    results[cookie_type] = {
        'total': total,
        'third_party': third_party,
        'third_party_pct': third_party_pct
    }

# Print summary
print('\n' + '='*80)
print('Cookie Setter Breakdown (Default State)')
print('='*80)
for cookie_type in cookie_types:
    data = results[cookie_type]
    print(f'{cookie_type:15s}: Total={data["total"]:6,}, 3P={data["third_party"]:6,} ({data["third_party_pct"]:5.1f}%)')

# Generate LaTeX table
latex_lines = []
latex_lines.append(r'  \begin{table}[!t]')
latex_lines.append(r'  \centering')
latex_lines.append(r'  \caption{Cookie Type Breakdown by Setter Origin. Percentages represent the share of cookies of each type set by third-party scripts.}')
latex_lines.append(r'  \label{tab:cookie-setter-breakdown}')
latex_lines.append(r'  \footnotesize')
latex_lines.append(r'  \begin{tabular}{p{3.2cm}|p{1.4cm}|p{1.8cm}|p{2.4cm}}')
latex_lines.append(r'  \toprule')
latex_lines.append(r'  \textbf{Cookie Type} & \textbf{Total} & \textbf{Set by 3P Scripts} & \textbf{\% Third-Party} \\')
latex_lines.append(r'  \midrule')

# Add rows
labels = {
    'Targeting': 'Targeting / Advertising',
    'Performance': 'Performance / Analytics',
    'Functional': 'Functional',
    'Necessary': 'Strictly Necessary',
    'Unknown': 'Unknown'
}

for i, cookie_type in enumerate(cookie_types):
    data = results[cookie_type]
    label = labels[cookie_type]
    
    if i % 2 == 0:  # Alternate gray rows
        prefix = r'  \cellcolor{gray!20}'
    else:
        prefix = r'  '
    
    line = f'{prefix}{label}\n      & {data["total"]:,}\n      & {data["third_party"]:,}\n'
    line += f'      & \\gradientcell{{{data["third_party_pct"]:.1f}}}{{0}}{{100}}{{red}}{{green}}{{40}}\\% \\\\'
    
    latex_lines.append(line)

latex_lines.append(r'  \bottomrule')
latex_lines.append(r'  \end{tabular}')
latex_lines.append(r'  \end{table}')

latex_output = '\n'.join(latex_lines)

# Save to file
output_file = 'table_cookie_setter_breakdown_updated.tex'
with open(output_file, 'w') as f:
    f.write(latex_output)

print(f'\n[OK] LaTeX table saved to: {output_file}')
print('\n' + '='*80)
print('Generated LaTeX Table:')
print('='*80)
print(latex_output)
