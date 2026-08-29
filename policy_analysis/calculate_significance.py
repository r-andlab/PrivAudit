# Calculate statistical significance for CCPA subject vs not-subject privacy policy comparisons.
import json
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import mannwhitneyu, chi2_contingency, fisher_exact
import warnings
warnings.filterwarnings('ignore')

def load_data():
    print("Loading data...")

    with open('ccpa_policy_audit_all_clean.json', 'r') as f:
        policy_data = json.load(f)

    subjectivity_df = pd.read_csv('policy_subjectivity_joined.csv')

    subjectivity_map = {}
    for _, row in subjectivity_df.iterrows():
        label = row['subjectivity_label']
        subjectivity_map[row['parent_domain']] = label
        subjectivity_map[row['raw_policy_domain']] = label

    rows = []
    for domain, data in policy_data.items():
        row = {'domain': domain}

        if 'rubric_assessment' in data:
            rubric = data['rubric_assessment']
            row['completeness_score'] = rubric.get('completeness_score')
            row['usability_score'] = rubric.get('usability_score')
            row['accuracy_score'] = rubric.get('accuracy_score')
            row['policy_contradiction'] = rubric.get('policy_contradiction')

            if 'disclosure_map' in rubric:
                disc = rubric['disclosure_map']
                row['data_collected'] = disc.get('data_collected')
                row['data_shared'] = disc.get('data_shared')
                row['purpose_of_collection'] = disc.get('purpose_of_collection')
                row['retention_period'] = disc.get('retention_period')
                row['right_to_access'] = disc.get('right_to_access')
                row['right_to_delete'] = disc.get('right_to_delete')
                row['opt_out'] = disc.get('opt_out')

        if 'behavioral_claims' in data:
            behav = data['behavioral_claims']
            row['honors_gpc'] = behav.get('honors_gpc')
            row['respects_dnt'] = behav.get('respects_dnt')
            row['sells_data'] = behav.get('sells_data')
            row['shares_with_third_parties'] = behav.get('shares_with_third_parties')
            row['sets_cookies_before_consent'] = behav.get('sets_cookies_before_consent')
            row['sets_cookies_after_rejecting_consent'] = behav.get('sets_cookies_after_rejecting_consent')
            row['deletes_cookies_on_rejection'] = behav.get('deletes_cookies_on_rejection')
            row['uses_tracking_only_after_consent'] = behav.get('uses_tracking_only_after_consent')

        row['mentions_online_practices'] = 'Not mentioned' not in data.get('online_data_practices', 'Not mentioned')
        row['mentions_offline_practices'] = 'Not mentioned' not in data.get('offline_data_practices', 'Not mentioned')

        rows.append(row)

    df = pd.DataFrame(rows)

    df['subjectivity'] = df['domain'].map(subjectivity_map)

    df = df.dropna(subset=['subjectivity'])

    print(f"Loaded {len(df)} policies")
    print(f"  - Subjected: {(df['subjectivity'] == 'subjected').sum()}")
    print(f"  - Not subjected: {(df['subjectivity'] == 'not_subjected').sum()}")

    return df

def mann_whitney_test(df, column, group_col='subjectivity'):
    subjected = df[df[group_col] == 'subjected'][column].dropna()
    not_subjected = df[df[group_col] == 'not_subjected'][column].dropna()

    if len(subjected) == 0 or len(not_subjected) == 0:
        return None, None, None, None

    statistic, pvalue = mannwhitneyu(subjected, not_subjected, alternative='two-sided')

    n1, n2 = len(subjected), len(not_subjected)
    r = 1 - (2*statistic) / (n1 * n2)

    return {
        'subjected_median': subjected.median(),
        'not_subjected_median': not_subjected.median(),
        'subjected_mean': subjected.mean(),
        'not_subjected_mean': not_subjected.mean(),
        'statistic': statistic,
        'p_value': pvalue,
        'effect_size_r': r,
        'n_subjected': n1,
        'n_not_subjected': n2
    }

def chi_square_test(df, column, group_col='subjectivity'):

    subjected = df[df[group_col] == 'subjected'][column].dropna()
    not_subjected = df[df[group_col] == 'not_subjected'][column].dropna()

    if len(subjected) == 0 or len(not_subjected) == 0:
        return None

    if column in ['honors_gpc', 'respects_dnt']:

        subjected_true = (subjected == True).sum()
        subjected_not_true = len(subjected) - subjected_true
        not_subjected_true = (not_subjected == True).sum()
        not_subjected_not_true = len(not_subjected) - not_subjected_true
    else:

        subjected_true = subjected.sum() if subjected.dtype == bool else (subjected == True).sum()
        subjected_not_true = len(subjected) - subjected_true
        not_subjected_true = not_subjected.sum() if not_subjected.dtype == bool else (not_subjected == True).sum()
        not_subjected_not_true = len(not_subjected) - not_subjected_true

    contingency = np.array([
        [subjected_true, subjected_not_true],
        [not_subjected_true, not_subjected_not_true]
    ])

    if contingency.min() < 5:
        _, pvalue = fisher_exact(contingency)
        test_used = 'fisher'
    else:
        chi2, pvalue, dof, expected = chi2_contingency(contingency)
        test_used = 'chi2'

    n = contingency.sum()
    phi2 = np.sum((contingency - np.outer(contingency.sum(axis=1),
                                          contingency.sum(axis=0)) / n)**2 /
                  np.outer(contingency.sum(axis=1), contingency.sum(axis=0)) * n)
    cramers_v = np.sqrt(phi2 / (n * (min(contingency.shape) - 1)))

    return {
        'subjected_true': subjected_true,
        'subjected_total': len(subjected),
        'subjected_pct': subjected_true / len(subjected) * 100,
        'not_subjected_true': not_subjected_true,
        'not_subjected_total': len(not_subjected),
        'not_subjected_pct': not_subjected_true / len(not_subjected) * 100,
        'p_value': pvalue,
        'effect_size_cramers_v': cramers_v,
        'test_used': test_used,
        'contingency_table': contingency.tolist()
    }

def main():

    df = load_data()

    print("\n" + "="*80)
    print("STATISTICAL SIGNIFICANCE TESTS FOR CCPA SUBJECT vs NOT-SUBJECT")
    print("="*80)

    print("\n" + "-"*80)
    print("1. RUBRIC SCORES (Mann-Whitney U Test)")
    print("-"*80)

    rubric_scores = ['completeness_score', 'usability_score', 'accuracy_score']
    rubric_results = {}

    for score in rubric_scores:
        result = mann_whitney_test(df, score)
        rubric_results[score] = result
        print(f"\n{score.replace('_', ' ').title()}:")
        print(f"  Subjected: median={result['subjected_median']:.2f}, mean={result['subjected_mean']:.2f} (n={result['n_subjected']})")
        print(f"  Not Subjected: median={result['not_subjected_median']:.2f}, mean={result['not_subjected_mean']:.2f} (n={result['n_not_subjected']})")
        print(f"  Mann-Whitney U statistic: {result['statistic']:.2f}")
        print(f"  p-value: {result['p_value']:.2e}")
        print(f"  Effect size (r): {result['effect_size_r']:.3f}")
        if result['p_value'] < 0.001:
            print(f"  *** Highly significant (p < 0.001)")
        elif result['p_value'] < 0.01:
            print(f"  ** Significant (p < 0.01)")
        elif result['p_value'] < 0.05:
            print(f"  * Significant (p < 0.05)")
        else:
            print(f"  Not significant (p >= 0.05)")

    print("\n" + "-"*80)
    print("2. DISCLOSURE COVERAGE (Chi-square/Fisher's Exact Test)")
    print("-"*80)

    disclosure_cols = ['data_collected', 'data_shared', 'purpose_of_collection',
                       'retention_period', 'right_to_access', 'right_to_delete', 'opt_out']
    disclosure_results = {}

    for col in disclosure_cols:
        result = chi_square_test(df, col)
        if result:
            disclosure_results[col] = result
            print(f"\n{col.replace('_', ' ').title()}:")
            print(f"  Subjected: {result['subjected_true']}/{result['subjected_total']} ({result['subjected_pct']:.1f}%)")
            print(f"  Not Subjected: {result['not_subjected_true']}/{result['not_subjected_total']} ({result['not_subjected_pct']:.1f}%)")
            print(f"  Test used: {result['test_used']}")
            print(f"  p-value: {result['p_value']:.2e}")
            print(f"  Effect size (Cramér's V): {result['effect_size_cramers_v']:.3f}")
            if result['p_value'] < 0.001:
                print(f"  *** Highly significant (p < 0.001)")
            elif result['p_value'] < 0.01:
                print(f"  ** Significant (p < 0.01)")
            elif result['p_value'] < 0.05:
                print(f"  * Significant (p < 0.05)")
            else:
                print(f"  Not significant (p >= 0.05)")

    print("\n" + "-"*80)
    print("3. BEHAVIORAL CLAIMS (Chi-square/Fisher's Exact Test)")
    print("-"*80)

    behavioral_cols = ['honors_gpc', 'respects_dnt', 'sells_data', 'shares_with_third_parties']
    behavioral_results = {}

    for col in behavioral_cols:
        result = chi_square_test(df, col)
        if result:
            behavioral_results[col] = result
            print(f"\n{col.replace('_', ' ').title()}:")
            print(f"  Subjected: {result['subjected_true']}/{result['subjected_total']} ({result['subjected_pct']:.1f}%)")
            print(f"  Not Subjected: {result['not_subjected_true']}/{result['not_subjected_total']} ({result['not_subjected_pct']:.1f}%)")
            print(f"  Test used: {result['test_used']}")
            print(f"  p-value: {result['p_value']:.2e}")
            print(f"  Effect size (Cramér's V): {result['effect_size_cramers_v']:.3f}")
            if result['p_value'] < 0.001:
                print(f"  *** Highly significant (p < 0.001)")
            elif result['p_value'] < 0.01:
                print(f"  ** Significant (p < 0.01)")
            elif result['p_value'] < 0.05:
                print(f"  * Significant (p < 0.05)")
            else:
                print(f"  Not significant (p >= 0.05)")

    print("\n" + "-"*80)
    print("4. DATA PRACTICES MENTIONS (Chi-square/Fisher's Exact Test)")
    print("-"*80)

    practices_cols = ['mentions_online_practices', 'mentions_offline_practices']
    practices_results = {}

    for col in practices_cols:
        result = chi_square_test(df, col)
        if result:
            practices_results[col] = result
            print(f"\n{col.replace('_', ' ').title()}:")
            print(f"  Subjected: {result['subjected_true']}/{result['subjected_total']} ({result['subjected_pct']:.1f}%)")
            print(f"  Not Subjected: {result['not_subjected_true']}/{result['not_subjected_total']} ({result['not_subjected_pct']:.1f}%)")
            print(f"  Test used: {result['test_used']}")
            print(f"  p-value: {result['p_value']:.2e}")
            print(f"  Effect size (Cramér's V): {result['effect_size_cramers_v']:.3f}")
            if result['p_value'] < 0.001:
                print(f"  *** Highly significant (p < 0.001)")
            elif result['p_value'] < 0.01:
                print(f"  ** Significant (p < 0.01)")
            elif result['p_value'] < 0.05:
                print(f"  * Significant (p < 0.05)")
            else:
                print(f"  Not significant (p >= 0.05)")

    all_results = {
        'rubric_scores': rubric_results,
        'disclosure_coverage': disclosure_results,
        'behavioral_claims': behavioral_results,
        'data_practices': practices_results
    }

    with open('statistical_significance_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print("\n" + "="*80)
    print("Results saved to: statistical_significance_results.json")
    print("="*80)

    print("\n" + "-"*80)
    print("LATEX TABLE FORMAT (for paper)")
    print("-"*80)
    print("\n% Add p-values to your claims:")
    print("% For rubric scores:")
    for score in rubric_scores:
        r = rubric_results[score]
        print(f"% {score}: p = {r['p_value']:.2e}, r = {r['effect_size_r']:.3f}")

    print("\n% For disclosure coverage:")
    for col in disclosure_cols:
        if col in disclosure_results:
            r = disclosure_results[col]
            print(f"% {col}: p = {r['p_value']:.2e}, V = {r['effect_size_cramers_v']:.3f}")

    print("\n% For behavioral claims:")
    for col in behavioral_cols:
        if col in behavioral_results:
            r = behavioral_results[col]
            print(f"% {col}: p = {r['p_value']:.2e}, V = {r['effect_size_cramers_v']:.3f}")

if __name__ == '__main__':
    main()
