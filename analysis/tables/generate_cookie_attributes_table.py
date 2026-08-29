# Generate cookie attributes and party split table for Default configuration
import pandas as pd

df = pd.read_csv('../Analysis/final_default_state_comprehensive_reclassified.csv', dtype=str, low_memory=False)

print(f"Loaded {len(df)} records from {df['website'].nunique()} websites")

cookie_types = ['Targeting', 'Performance', 'Functional', 'Necessary', 'Unknown']

def has_value(val):
    if pd.isna(val):
        return False
    val_str = str(val).strip().lower()
    return val_str not in ['', 'nan', 'none', 'null']

def is_true(val):
    if pd.isna(val):
        return False
    val_str = str(val).strip().lower()
    return val_str in ['true', '1', 'yes']

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

default_df = df[df['initial_cookies'].apply(has_value)].copy()

default_df['category_normalized'] = default_df['category'].apply(norm_category)

print(f"\nDefault configuration cookies: {len(default_df)}")

results = []

for cookie_type in cookie_types:
    type_df = default_df[default_df['category_normalized'] == cookie_type].copy()

    n = len(type_df)

    if n == 0:
        continue

    secure_pct = (type_df['secure'].apply(is_true).sum() / n) * 100
    httponly_pct = (type_df['httpOnly'].apply(is_true).sum() / n) * 100

    samesite_count = 0
    for val in type_df['sameSite']:
        if has_value(val):
            val_str = str(val).strip().lower()
            if val_str not in ['none', 'null']:
                samesite_count += 1
    samesite_pct = (samesite_count / n) * 100

    session_count = 0
    for val in type_df['expires']:
        if pd.isna(val) or str(val).strip() == '':
            session_count += 1
        else:
            val_str = str(val).strip()
            if val_str == '-1' or val_str == 'Session':
                session_count += 1
    session_pct = (session_count / n) * 100

    third_party_count = (type_df['script_is_third_party'] == 'Yes').sum()
    third_party_pct = (third_party_count / n) * 100
    first_party_pct = 100 - third_party_pct

    results.append({
        'cookie_type': cookie_type,
        'n': n,
        'secure': secure_pct,
        'httponly': httponly_pct,
        'samesite': samesite_pct,
        'session': session_pct,
        'first_party': first_party_pct,
        'third_party': third_party_pct
    })

    print(f"\n{cookie_type}:")
    print(f"  N: {n:,}")
    print(f"  Secure: {secure_pct:.1f}%")
    print(f"  HttpOnly: {httponly_pct:.1f}%")
    print(f"  SameSite: {samesite_pct:.1f}%")
    print(f"  Session: {session_pct:.1f}%")
    print(f"  First-Party: {first_party_pct:.1f}%")
    print(f"  Third-Party: {third_party_pct:.1f}%")

total_n = sum(r['n'] for r in results)
total_secure = sum(r['secure'] * r['n'] for r in results) / total_n
total_httponly = sum(r['httponly'] * r['n'] for r in results) / total_n
total_samesite = sum(r['samesite'] * r['n'] for r in results) / total_n
total_session = sum(r['session'] * r['n'] for r in results) / total_n
total_first_party = sum(r['first_party'] * r['n'] for r in results) / total_n
total_third_party = sum(r['third_party'] * r['n'] for r in results) / total_n

print(f"\nTotal:")
print(f"  N: {total_n:,}")
print(f"  Secure: {total_secure:.1f}%")
print(f"  HttpOnly: {total_httponly:.1f}%")
print(f"  SameSite: {total_samesite:.1f}%")
print(f"  Session: {total_session:.1f}%")
print(f"  First-Party: {total_first_party:.1f}%")
print(f"  Third-Party: {total_third_party:.1f}%")

print("\n" + "="*80)
print("GENERATING LATEX TABLE")
print("="*80)

latex_lines = []
latex_lines.append(r"  \begin{table}[!t]")
latex_lines.append(r"    \centering")
latex_lines.append(r"    \footnotesize")
latex_lines.append(r"    \caption{Adoption of cookie security attributes and first-/third-party split by cookie type (Default")
latex_lines.append(r"    browsing configuration). Third-party classification is based on script attribution.}")
latex_lines.append(r"    \label{tab:cookie-attributes-party}")
latex_lines.append(r"    \begin{tabular}{p{1.2cm}")
latex_lines.append(r"                    >{\raggedright\arraybackslash}p{0.5cm}")
latex_lines.append(r"                    >{\raggedright\arraybackslash}p{0.7cm}")
latex_lines.append(r"                    >{\raggedright\arraybackslash}p{0.7cm}")
latex_lines.append(r"                    >{\raggedright\arraybackslash}p{0.7cm}")
latex_lines.append(r"                    >{\raggedright\arraybackslash}p{0.6cm}")
latex_lines.append(r"                    >{\raggedright\arraybackslash}p{0.7cm}")
latex_lines.append(r"                    >{\raggedright\arraybackslash}p{0.6cm}}")
latex_lines.append(r"    \toprule")
latex_lines.append(r"    Cookie Type & N & Secure & HttpOnly & SameSite & Session & First-Party & Third-Party \\")
latex_lines.append(r"    \midrule")

for i, result in enumerate(results):
    if i % 2 == 1:
        row_prefix = r"    \rowcolor{gray!20}"
    else:
        row_prefix = "    "

    line = f"{row_prefix}{result['cookie_type']} & {result['n']:,} & "
    line += f"\\gradientcell{{{result['secure']:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
    line += f"\\gradientcell{{{result['httponly']:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
    line += f"\\gradientcell{{{result['samesite']:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
    line += f"\\gradientcell{{{result['session']:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
    line += f"\\gradientcell{{{result['first_party']:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
    line += f"\\gradientcell{{{result['third_party']:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% \\\\"

    latex_lines.append(line)

latex_lines.append(r"    \midrule")

total_line = f"    \\textbf{{Total}} & \\textbf{{{total_n:,}}} & "
total_line += f"\\gradientcell{{{total_secure:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
total_line += f"\\gradientcell{{{total_httponly:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
total_line += f"\\gradientcell{{{total_samesite:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
total_line += f"\\gradientcell{{{total_session:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\% & "
total_line += f"\\textbf{{\\gradientcell{{{total_first_party:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\%}} & "
total_line += f"\\textbf{{\\gradientcell{{{total_third_party:.1f}}}{{1}}{{100}}{{red}}{{green}}{{40}}\\%}} \\\\"

latex_lines.append(total_line)
latex_lines.append(r"    \bottomrule")
latex_lines.append(r"    \end{tabular}")
latex_lines.append(r"  \end{table}")

print()
for line in latex_lines:
    print(line)

output_file = 'table_cookie_attributes.tex'
with open(output_file, 'w') as f:
    f.write('\n'.join(latex_lines))

print(f"\n[OK] Saved LaTeX table to: {output_file}")
print()
