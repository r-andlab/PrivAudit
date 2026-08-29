# Generate updated policy audit table treating Unknown as Not-Subject.
import pandas as pd
import json
import pickle

print("Loading data files...")
data_source = pd.read_csv('data_source.csv')
with open('ccpa_policy_audit_data_source_mapped.json', 'r') as f:
    audit_mapped = json.load(f)

data_source['website_norm'] = data_source['website'].str.strip().str.lower()
website_to_ccpa = dict(zip(data_source['website_norm'], data_source['ccpa']))

def get_ccpa_category(ccpa_status):
    if pd.isna(ccpa_status):
        return 'Not-Subject'
    ccpa_status = str(ccpa_status).lower()
    if 'subjected' in ccpa_status:
        return 'Subject'
    else:
        return 'Not-Subject'

website_categories = {}
for website in audit_mapped.keys():
    ccpa_status = website_to_ccpa.get(website, None)
    category = get_ccpa_category(ccpa_status)
    website_categories[website] = category

print(f"\nTotal websites with audit data: {len(website_categories)}")
print(f"Subject: {sum(1 for c in website_categories.values() if c == 'Subject')}")
print(f"Not-Subject: {sum(1 for c in website_categories.values() if c == 'Not-Subject')}")

stats = {
    'Subject': {
        'count': 0,
        'disclosure': {},
        'mentions': {},
        'behavioral': {}
    },
    'Not-Subject': {
        'count': 0,
        'disclosure': {},
        'mentions': {},
        'behavioral': {}
    }
}

disclosure_keys = {
    'data_collected': 'Data Collection',
    'data_shared': 'Data Sharing',
    'opt_out': 'Data Collection Opt Out',
    'purpose_of_collection': 'Purpose of Collection',
    'retention_period': 'Data Retention Period',
    'right_to_access': 'Right to Access',
    'right_to_delete': 'Right to Delete'
}

behavioral_keys = {
    'deletes_cookies_on_rejection': 'Deletes Cookie After Rejecting Consent',
    'sets_cookies_after_rejecting_consent': 'Sets Cookies After Rejecting Consent',
    'sets_cookies_before_consent': 'Sets Cookies Before Consent',
    'uses_tracking_only_after_consent': 'Tracking Only After Consent',
    'sells_data': 'Sells Data',
    'shares_with_third_parties': 'Shares Data with Third Parties',
    'honors_gpc': 'Honors GPC',
    'respects_dnt': 'Honors DNT'
}

for category in ['Subject', 'Not-Subject']:
    for key in disclosure_keys.values():
        stats[category]['disclosure'][key] = {'true': 0, 'false': 0}

    for key in behavioral_keys.values():
        stats[category]['behavioral'][key] = {'true': 0, 'false': 0, 'unspecified': 0}

    stats[category]['mentions']['Cookies'] = {'true': 0, 'false': 0}
    stats[category]['mentions']['CCPA'] = {'true': 0, 'false': 0}
    stats[category]['mentions']['Online Data Collection'] = {'true': 0, 'false': 0}
    stats[category]['mentions']['Offline Data Collection'] = {'true': 0, 'false': 0}

print("\nProcessing audit data...")
for website, data in audit_mapped.items():
    category = website_categories.get(website, 'Not-Subject')
    stats[category]['count'] += 1

    audit_data = data.get('audit_data', {})
    rubric = audit_data.get('rubric_assessment', {})
    disclosure_map = rubric.get('disclosure_map', {})
    behavioral_claims = audit_data.get('behavioral_claims', {})
    online_practices = audit_data.get('online_data_practices', '')
    offline_practices = audit_data.get('offline_data_practices', '')

    for json_key, display_name in disclosure_keys.items():
        value = disclosure_map.get(json_key, False)
        if value:
            stats[category]['disclosure'][display_name]['true'] += 1
        else:
            stats[category]['disclosure'][display_name]['false'] += 1

    for json_key, display_name in behavioral_keys.items():
        value = behavioral_claims.get(json_key, 'unspecified')
        if isinstance(value, bool):
            if value:
                stats[category]['behavioral'][display_name]['true'] += 1
            else:
                stats[category]['behavioral'][display_name]['false'] += 1
        else:
            value_str = str(value).lower()
            if value_str == 'true':
                stats[category]['behavioral'][display_name]['true'] += 1
            elif value_str == 'false':
                stats[category]['behavioral'][display_name]['false'] += 1
            else:
                stats[category]['behavioral'][display_name]['unspecified'] += 1

    online_lower = online_practices.lower() if online_practices else ''
    offline_lower = offline_practices.lower() if offline_practices else ''

    if 'cookie' in online_lower:
        stats[category]['mentions']['Cookies']['true'] += 1
    else:
        stats[category]['mentions']['Cookies']['false'] += 1

    if 'ccpa' in online_lower or 'california consumer privacy act' in online_lower:
        stats[category]['mentions']['CCPA']['true'] += 1
    else:
        stats[category]['mentions']['CCPA']['false'] += 1

    if online_practices and len(online_practices.strip()) > 20:
        stats[category]['mentions']['Online Data Collection']['true'] += 1
    else:
        stats[category]['mentions']['Online Data Collection']['false'] += 1

    if offline_practices and len(offline_practices.strip()) > 20:
        stats[category]['mentions']['Offline Data Collection']['true'] += 1
    else:
        stats[category]['mentions']['Offline Data Collection']['false'] += 1

with open('policy_audit_statistics.pkl', 'wb') as f:
    pickle.dump(stats, f)

print(f"\n[OK] Saved statistics to policy_audit_statistics.pkl")
print(f"\nSample sizes:")
print(f"  Subject: {stats['Subject']['count']}")
print(f"  Not-Subject: {stats['Not-Subject']['count']}")

def gradient_cell(value, vmin=0, vmax=100):
    return f"\\gradientcell{{{value:.1f}}}{{{vmin}}}{{{vmax}}}{{red}}{{green}}{{40}}\\%"

def gradient_cell_with_text(value, text, vmin=0, vmax=100):
    return f"\\gradientcellwtext{{{value:.1f}}}{{{vmin}}}{{{vmax}}}{{red}}{{green}}{{40}}{{{text}}}"

latex_lines = []
latex_lines.append("\\begin{table*}[!t]")
latex_lines.append("\\centering")
latex_lines.append("")
latex_lines.append(f"\\caption{{Disclosure coverage, behavioral claims, and mentions of privacy practices in privacy policies. For disclosures and mentions, values are ``True'' percentages. For behavioral claims, we show True (T), False (F), and Unspecified (U) percentages. Updated for {stats['Subject']['count'] + stats['Not-Subject']['count']} websites with LLM policy audits (n={stats['Subject']['count']} Subject, n={stats['Not-Subject']['count']} Not-Subject).]]}}")
latex_lines.append("\\label{tab:policy-results-overall}")
latex_lines.append("\\footnotesize")
latex_lines.append("\\begin{tabular}{p{2.5cm}|p{1.3cm}|p{1.3cm}|p{11.2cm}}")
latex_lines.append("\\toprule")
latex_lines.append("\\textbf{Metric / Claim} & \\textbf{\\texttt{Subject}} & \\textbf{\\texttt{Not-Subject}} & \\textbf{Example Policy excerpt (True cases)} \\\\")
latex_lines.append("\\midrule")

latex_lines.append(f"\\textbf{{Disclosure Coverage}} & \\textbf{{$n={stats['Subject']['count']}$}} & \\textbf{{$n={stats['Not-Subject']['count']}$}} &  \\\\")
latex_lines.append("\\hline")

disclosure_examples = {
    'Data Collection': "``The information we collect [includes]...interactions, device information, [and] location information''",
    'Data Sharing': "``We may share your information with our service providers… advertisers...[and] affiliates''",
    'Data Collection Opt Out': "``[C]ontrol whether [this website] shares your personal information...by using the 'Data sharing...' option''",
    'Purpose of Collection': "``We use the information we collect to provide and operate [feature]...improve and personalize [feature]...foster safety and security...[and] measure and analyze''",
    'Data Retention Period': "``We keep different types of information for different period...cookies up to 13 months...ad interactions up to 12 months...[and] communications up to 18 months''",
    'Right to Access': "``You can access, correct, or modify the information...You can download a copy of your information''",
    'Right to Delete': "``If you follow the instructions... your account will be deactivated and your data will be queued for deletion.''"
}

row_num = 0
for metric in ['Data Collection', 'Data Sharing', 'Data Collection Opt Out', 'Purpose of Collection',
               'Data Retention Period', 'Right to Access', 'Right to Delete']:
    subject_pct = 100 * stats['Subject']['disclosure'][metric]['true'] / stats['Subject']['count']
    not_subject_pct = 100 * stats['Not-Subject']['disclosure'][metric]['true'] / stats['Not-Subject']['count']

    if row_num % 2 == 1:
        latex_lines.append(f"\\cellcolor{{gray!20}}{metric}")
    else:
        latex_lines.append(metric)

    latex_lines.append(f"                                    & {gradient_cell(subject_pct, 1, 100)}")
    latex_lines.append(f"                                    & {gradient_cell(not_subject_pct, 1, 100)}")

    if row_num % 2 == 1:
        latex_lines.append(f"                                    &\\cellcolor{{gray!20}}{disclosure_examples[metric]} \\\\")
    else:
        latex_lines.append(f"                                    & {disclosure_examples[metric]} \\\\")

    row_num += 1

latex_lines.append("\\midrule")
latex_lines.append(f"\\textbf{{Mentions}} & \\textbf{{$n={stats['Subject']['count']}$}} & \\textbf{{$n={stats['Not-Subject']['count']}$}} & \\\\")
latex_lines.append("\\hline")

mention_examples = {
    'Cookies': "``We use cookies, pixels and other Tracking Technologies to collect information about you''",
    'CCPA': "``California residents can submit requests to opt out of the sale of personal information under the...(CCPA). ''",
    'Online Data Collection': "``We may send...cookies...We may also use other similar technologies such as tracking pixels, tags, or similar tools''",
    'Offline Data Collection': "``Personal information may be collected ...when you visit our stores... or deal with customer service''"
}

row_num = 0
for mention in ['Cookies', 'CCPA', 'Online Data Collection', 'Offline Data Collection']:
    subject_pct = 100 * stats['Subject']['mentions'][mention]['true'] / stats['Subject']['count']
    not_subject_pct = 100 * stats['Not-Subject']['mentions'][mention]['true'] / stats['Not-Subject']['count']

    if row_num % 2 == 0:
        latex_lines.append(f"\\cellcolor{{gray!20}}{mention}")
    else:
        latex_lines.append(mention)

    latex_lines.append(f"                                    & {gradient_cell(subject_pct, 1, 100)}")
    latex_lines.append(f"                                    & {gradient_cell(not_subject_pct, 1, 100)}")

    if row_num % 2 == 0:
        latex_lines.append(f"                                    &\\cellcolor{{gray!20}}{mention_examples[mention]} \\\\")
    else:
        latex_lines.append(f"                                    & {mention_examples[mention]} \\\\")

    row_num += 1

latex_lines.append("\\midrule")
latex_lines.append(f"\\textbf{{Behavioral Claims}} & \\textbf{{$n={stats['Subject']['count']}$}} & \\textbf{{$n={stats['Not-Subject']['count']}$}} & \\\\")
latex_lines.append("\\hline")

behavioral_examples = {
    'Deletes Cookie After Rejecting Consent': "``[C]lick here to...control, disable, or delete [cookies].''",
    'Sets Cookies After Rejecting Consent': "No true cases.",
    'Sets Cookies Before Consent': "``If you continue using [website] we will assume that you are happy to receive cookies.''",
    'Tracking Only After Consent': "``By default, you are opted out of all cookie categories except strictly necessary cookies.''",
    'Sells Data': "``We may disclose certain personal information in exchange for services, insights, or other valuable consideration.''",
    'Shares Data with Third Parties': "``We may share your personal information with...service providers''",
    'Honors GPC': "``You may use the Global Privacy Control (GPC)...If GitHub detects the GPC signal from your device, GitHub will not share your data.''",
    'Honors DNT': "``If your browser sends a Do Not Track (DNT) signal, GitHub will not set non-essential cookies and will not load third party resources''"
}

row_num = 0
for claim in ['Deletes Cookie After Rejecting Consent', 'Sets Cookies After Rejecting Consent',
              'Sets Cookies Before Consent', 'Tracking Only After Consent', 'Sells Data',
              'Shares Data with Third Parties', 'Honors GPC', 'Honors DNT']:

    subject_true_pct = 100 * stats['Subject']['behavioral'][claim]['true'] / stats['Subject']['count']
    subject_false_pct = 100 * stats['Subject']['behavioral'][claim]['false'] / stats['Subject']['count']
    subject_unspec_pct = 100 * stats['Subject']['behavioral'][claim]['unspecified'] / stats['Subject']['count']

    not_subject_true_pct = 100 * stats['Not-Subject']['behavioral'][claim]['true'] / stats['Not-Subject']['count']
    not_subject_false_pct = 100 * stats['Not-Subject']['behavioral'][claim]['false'] / stats['Not-Subject']['count']
    not_subject_unspec_pct = 100 * stats['Not-Subject']['behavioral'][claim]['unspecified'] / stats['Not-Subject']['count']

    if row_num % 2 == 0:
        latex_lines.append(f"\\cellcolor{{gray!20}}{claim}")
    else:
        latex_lines.append(claim)

    subject_true_text = f'T: {subject_true_pct:.1f}\\%'
    subject_false_text = f'F: {subject_false_pct:.1f}\\%'
    subject_unspec_text = f'U: {subject_unspec_pct:.1f}\\%'

    latex_lines.append("                                    &\\begin{tabular}[t]{@{}p{1.3cm}}")
    latex_lines.append(f"                                        {gradient_cell_with_text(subject_true_pct, subject_true_text, 0, 100)}\\\\")
    latex_lines.append(f"                                        {gradient_cell_with_text(subject_false_pct, subject_false_text, 0, 100)}\\\\")
    latex_lines.append(f"                                        {gradient_cell_with_text(subject_unspec_pct, subject_unspec_text, 0, 100)}")
    latex_lines.append("                                    \\end{tabular}")

    not_subject_true_text = f'T: {not_subject_true_pct:.1f}\\%'
    not_subject_false_text = f'F: {not_subject_false_pct:.1f}\\%'
    not_subject_unspec_text = f'U: {not_subject_unspec_pct:.1f}\\%'

    latex_lines.append("                                    &\\begin{tabular}[t]{@{}p{1.3cm}}")
    latex_lines.append(f"                                        {gradient_cell_with_text(not_subject_true_pct, not_subject_true_text, 0, 100)}\\\\")
    latex_lines.append(f"                                        {gradient_cell_with_text(not_subject_false_pct, not_subject_false_text, 0, 100)}\\\\")
    latex_lines.append(f"                                        {gradient_cell_with_text(not_subject_unspec_pct, not_subject_unspec_text, 0, 100)}")
    latex_lines.append("                                    \\end{tabular}")

    if row_num % 2 == 0:
        latex_lines.append(f"                                    &\\cellcolor{{gray!20}}{behavioral_examples[claim]} \\\\")
    else:
        latex_lines.append(f"                                    & {behavioral_examples[claim]} \\\\")

    row_num += 1

latex_lines.append("\\bottomrule")
latex_lines.append("\\end{tabular}%")
latex_lines.append("\\end{table*}")

latex_content = '\n'.join(latex_lines)
with open('updated_policy_table.tex', 'w') as f:
    f.write(latex_content)

print(f"[OK] Generated updated_policy_table.tex")
print(f"\n--- Key Statistics ---")
print(f"Subject (n={stats['Subject']['count']}):")
print(f"  Data Collection: {100 * stats['Subject']['disclosure']['Data Collection']['true'] / stats['Subject']['count']:.1f}%")
print(f"  CCPA mention: {100 * stats['Subject']['mentions']['CCPA']['true'] / stats['Subject']['count']:.1f}%")
print(f"  Honors GPC (T/F/U): {100 * stats['Subject']['behavioral']['Honors GPC']['true'] / stats['Subject']['count']:.1f}% / {100 * stats['Subject']['behavioral']['Honors GPC']['false'] / stats['Subject']['count']:.1f}% / {100 * stats['Subject']['behavioral']['Honors GPC']['unspecified'] / stats['Subject']['count']:.1f}%")

print(f"\nNot-Subject (n={stats['Not-Subject']['count']}):")
print(f"  Data Collection: {100 * stats['Not-Subject']['disclosure']['Data Collection']['true'] / stats['Not-Subject']['count']:.1f}%")
print(f"  CCPA mention: {100 * stats['Not-Subject']['mentions']['CCPA']['true'] / stats['Not-Subject']['count']:.1f}%")
print(f"  Honors GPC (T/F/U): {100 * stats['Not-Subject']['behavioral']['Honors GPC']['true'] / stats['Not-Subject']['count']:.1f}% / {100 * stats['Not-Subject']['behavioral']['Honors GPC']['false'] / stats['Not-Subject']['count']:.1f}% / {100 * stats['Not-Subject']['behavioral']['Honors GPC']['unspecified'] / stats['Not-Subject']['count']:.1f}%")
