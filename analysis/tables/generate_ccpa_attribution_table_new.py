# Generate CCPA attribution configs table with reclassified data.
import pandas as pd
import numpy as np

df = pd.read_csv('../Analysis/final_default_state_comprehensive_reclassified.csv', dtype=str, low_memory=False)

print(f'Loaded {len(df)} records from {df["website"].nunique()} websites')

def has_value(val):
    if pd.isna(val):
        return False
    val_str = str(val).strip().lower()
    return val_str not in ['', 'nan', 'none', 'null']

def normalize_ccpa(val: str) -> str:
    if not isinstance(val, str):
        return 'Not-Subject'
    v = val.strip()
    if v == 'Subject to CCPA':
        return 'Subject'
    else:
        return 'Not-Subject'

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

df['Cookie_Type'] = df['category'].apply(norm_category)
df['CCPA_Group'] = df['CCPA_Category'].apply(normalize_ccpa)
df['is_3p'] = df['script_is_third_party'].apply(is_third_party)

configs = {
    'Default': 'initial_cookies',
    'DNT': 'do_not_track',
    'Block3P': 'block_3rd_party',
    'uBlock': 'ublock',
    'GPC': 'gpc_enabled'
}

cookie_types = ['Targeting', 'Performance', 'Functional', 'Necessary', 'Unknown']

results = {}

for ccpa_group in ['Subject', 'Not-Subject']:
    results[ccpa_group] = {}
    ccpa_df = df[df['CCPA_Group'] == ccpa_group]

    for cookie_type in cookie_types:
        results[ccpa_group][cookie_type] = {}
        type_df = ccpa_df[ccpa_df['Cookie_Type'] == cookie_type]

        for config_name, config_col in configs.items():

            mask = type_df[config_col].apply(has_value)
            count = mask.sum()
            results[ccpa_group][cookie_type][config_name] = count

            if config_name == 'Default':
                if count > 0:
                    third_party_count = type_df[mask]['is_3p'].sum()
                    third_party_pct = (third_party_count / count) * 100
                else:
                    third_party_pct = 0.0
                results[ccpa_group][cookie_type]['3rd_party_pct'] = third_party_pct

for ccpa_group in ['Subject', 'Not-Subject']:
    results[ccpa_group]['Total'] = {}
    for config_name in configs.keys():
        total = sum(results[ccpa_group][ct][config_name] for ct in cookie_types)
        results[ccpa_group]['Total'][config_name] = total

    default_total = results[ccpa_group]['Total']['Default']
    if default_total > 0:
        ccpa_df = df[df['CCPA_Group'] == ccpa_group]
        default_mask = ccpa_df['initial_cookies'].apply(has_value)
        third_party_total = ccpa_df[default_mask]['is_3p'].sum()
        third_party_pct = (third_party_total / default_total) * 100
    else:
        third_party_pct = 0.0
    results[ccpa_group]['Total']['3rd_party_pct'] = third_party_pct

print('\n' + '='*100)
print('Cookie Counts by Type, CCPA Status, and Configuration')
print('='*100)

print('\nSUBJECT TO CCPA:')
for cookie_type in cookie_types + ['Total']:
    print(f'\n{cookie_type}:')
    data = results['Subject'][cookie_type]
    print(f'  Default: {data["Default"]:,} ({data["3rd_party_pct"]:.1f}% 3rd-party)')
    print(f'  DNT: {data["DNT"]:,}, Block3P: {data["Block3P"]:,}, uBlock: {data["uBlock"]:,}, GPC: {data["GPC"]:,}')

print('\n\nNOT SUBJECT TO CCPA:')
for cookie_type in cookie_types + ['Total']:
    print(f'\n{cookie_type}:')
    data = results['Not-Subject'][cookie_type]
    print(f'  Default: {data["Default"]:,} ({data["3rd_party_pct"]:.1f}% 3rd-party)')
    print(f'  DNT: {data["DNT"]:,}, Block3P: {data["Block3P"]:,}, uBlock: {data["uBlock"]:,}, GPC: {data["GPC"]:,}')

latex_lines = []
latex_lines.append(r'  \begin{table*}[!t]')
latex_lines.append(r'  \caption{Cookie counts by type, CCPA applicability, and privacy configuration. Default state shows N cookies and third-party attribution percentage.')
latex_lines.append(r'  Configuration columns show total cookies across all websites.}')
latex_lines.append(r'  \label{tab:ccpa-attribution-configs}')
latex_lines.append(r'  \centering')
latex_lines.append(r'  \tiny')
latex_lines.append(r'  \begin{tabular}{lrrrrrrrrrrrrr}')
latex_lines.append(r'  \toprule')
latex_lines.append(r'  \textbf{Cookie Type} & \multicolumn{6}{c}{\textbf{Subject to CCPA}} & \multicolumn{6}{c}{\textbf{Not Subject to CCPA}} \\')
latex_lines.append(r'  \cmidrule(lr){2-7} \cmidrule(lr){8-13}')
latex_lines.append(r'   & \textbf{Default} & \textbf{3rd-Pty} & \textbf{DNT} & \textbf{Block3P} & \textbf{uBlock} & \textbf{GPC} & \textbf{Default} & \textbf{3rd-Pty} &')
latex_lines.append(r'  \textbf{DNT} & \textbf{Block3P} & \textbf{uBlock} & \textbf{GPC} \\')
latex_lines.append(r'   & \textbf{N} & \textbf{\%} & \textbf{N} & \textbf{N} & \textbf{N} & \textbf{N} & \textbf{N} & \textbf{\%} & \textbf{N} & \textbf{N} & \textbf{N} &')
latex_lines.append(r'  \textbf{N} \\')
latex_lines.append(r'  \midrule')

for cookie_type in cookie_types:
    subj_data = results['Subject'][cookie_type]
    notsubj_data = results['Not-Subject'][cookie_type]

    line = f'  {cookie_type:12s} & {subj_data["Default"]:5,} & {subj_data["3rd_party_pct"]:5.1f}\\% & '
    line += f'{subj_data["DNT"]:5,} & {subj_data["Block3P"]:5,} & {subj_data["uBlock"]:5,} & {subj_data["GPC"]:5,} & '
    line += f'{notsubj_data["Default"]:5,} & {notsubj_data["3rd_party_pct"]:5.1f}\\% & '
    line += f'{notsubj_data["DNT"]:5,} & {notsubj_data["Block3P"]:5,} & {notsubj_data["uBlock"]:5,} & {notsubj_data["GPC"]:5,} \\\\'

    latex_lines.append(line)

latex_lines.append(r'  \midrule')

subj_data = results['Subject']['Total']
notsubj_data = results['Not-Subject']['Total']

total_line = f'  \\textbf{{Total}} & \\textbf{{{subj_data["Default"]:5,}}} & \\textbf{{{subj_data["3rd_party_pct"]:5.1f}\\%}} & '
total_line += f'\\textbf{{{subj_data["DNT"]:5,}}} & \\textbf{{{subj_data["Block3P"]:5,}}} & \\textbf{{{subj_data["uBlock"]:5,}}} & \\textbf{{{subj_data["GPC"]:5,}}} & '
total_line += f'\\textbf{{{notsubj_data["Default"]:5,}}} & \\textbf{{{notsubj_data["3rd_party_pct"]:5.1f}\\%}} & '
total_line += f'\\textbf{{{notsubj_data["DNT"]:5,}}} & \\textbf{{{notsubj_data["Block3P"]:5,}}} & \\textbf{{{notsubj_data["uBlock"]:5,}}} & \\textbf{{{notsubj_data["GPC"]:5,}}} \\\\'

latex_lines.append(total_line)
latex_lines.append(r'  \bottomrule')
latex_lines.append(r'  \end{tabular}')
latex_lines.append(r'  \end{table*}')

latex_output = '\n'.join(latex_lines)

output_file = 'table_ccpa_attribution_configs_updated.tex'
with open(output_file, 'w') as f:
    f.write(latex_output)

print(f'\n\n[OK] LaTeX table saved to: {output_file}')
print('\n' + '='*100)
print('Generated LaTeX Table:')
print('='*100)
print(latex_output)
