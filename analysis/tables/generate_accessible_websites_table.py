# Generate LaTeX table for all 1002 accessible websites by CCPA category.
import pandas as pd

data_source = pd.read_csv('data_source.csv', dtype=str)

failed_websites = {
    'gfycat.com',
    'limelight.com',
    'makeupalley.com',
    'stylebistro.com',
    'cesarsway.com',
    'mygreatlakes.org',
    'studentloans.gov',
    'mysimon.com',
    'airasia.com',
    'myntra.com',
    'ryanair.com',
    'truecar.com'
}

data_source['website_clean'] = data_source['website'].fillna('').str.replace(r'\r\n', '', regex=True).str.strip()

data_source = data_source.drop_duplicates(subset=['website_clean'], keep='first')

accessible = data_source[~data_source['website_clean'].isin(failed_websites)].copy()
accessible = accessible[accessible['website_clean'] != '']

print(f'Total websites in data source: {len(data_source)}')
print(f'Failed websites excluded: {len(failed_websites)}')
print(f'Accessible websites: {len(accessible)}')

def normalize_ccpa(val: str) -> str:
    if not isinstance(val, str):
        return "Unknown Eligibility"
    v = val.strip().lower()

    if v == "government":
        return "Government"
    elif v == "non_profit":
        return "Non-Profit"
    elif v == "revenue_not_suff":
        return "Revenue Not Sufficient"
    elif v in ["subjected", "subjected, location", "subjected,location"]:
        return "Subject to CCPA"
    elif v == "unknown":
        return "Unknown Eligibility"
    else:
        return "Unknown Eligibility"

accessible['CCPA_Category'] = accessible['ccpa'].apply(normalize_ccpa)

category_counts = accessible['CCPA_Category'].value_counts().to_dict()

categories = [
    ("Government", "Public sector domains"),
    ("Non-Profit", "U.S.-based nonprofit organizations"),
    ("Revenue Not Sufficient", "For-profits below CCPA threshold"),
    ("Subject to CCPA", "For-profits meeting CCPA applicability criteria"),
    ("Unknown Eligibility", "For-profits with indeterminate eligibility"),
]

print("\nCCPA Category Breakdown (1002 Accessible Websites):")
total = 0
for cat, desc in categories:
    count = category_counts.get(cat, 0)
    total += count
    print(f"  {cat:25s}: {count:4d}")
print(f"  {'Total':25s}: {total:4d}")

latex = r"""\begin{table}[!t]
    \centering
    \footnotesize
    \caption{\textbf{Website Categorization by CCPA Applicability and Organizational Type (1,002 Accessible Websites).}}
    \label{tab:accessible-websites-categories}
    \begin{tabular}{l  p{4cm}  r}
    \toprule
    \textbf{Category} & \textbf{Description} & \textbf{Count} \\
    \midrule
"""

for i, (cat, desc) in enumerate(categories):
    count = category_counts.get(cat, 0)
    if i % 2 == 0:
        latex += f"    \\cellcolor{{gray!20}}{cat} & \\cellcolor{{gray!20}}{desc} & \\cellcolor{{gray!20}}{count}\\\\\n"
    else:
        latex += f"    {cat} & {desc} & {count} \\\\\n"

latex += r"""    \midrule
    \textbf{Total} & & \textbf{""" + str(total) + r"""} \\
    \bottomrule
    \end{tabular}
  \end{table}"""

output_file = "table_accessible_websites_by_ccpa.tex"
with open(output_file, 'w') as f:
    f.write(latex)

print(f"\nLaTeX table saved to: {output_file}")
print("\n" + "="*80)
print("Generated LaTeX Table:")
print("="*80)
print(latex)
