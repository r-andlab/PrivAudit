# Usage: python analyze_inner_allconfigs.py  |  Inner-page vs homepage tracking across all crawled privacy configurations.
import glob, numpy as np, pandas as pd
from scipy.stats import wilcoxon
import os
BASE = os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRAWL = f"{BASE}/data/inner_page_crawl"
rng = np.random.default_rng(20260724)
CONFIGS = ['default', 'gpc', 'dnt', 'block3p']
N_TARGET = sum(1 for l in open(f"{CRAWL}/full_sites.txt") if l.strip())

ref = pd.read_csv(f"{BASE}/data/final_default_state_comprehensive_reclassified.csv", low_memory=False)
namecat = ref.groupby('cookie_name')['category'].agg(lambda s: s.value_counts().idxmax()).to_dict()
scol = 'CCPA_Category' if 'CCPA_Category' in ref.columns else 'ccpa'
site_status = ref.groupby('website')[scol].agg(lambda s: s.value_counts().idxmax()).to_dict()

def boot_ci(delta, n=10000):
    b = np.array([rng.choice(delta, size=len(delta), replace=True).mean() for _ in range(n)])
    return np.percentile(b, [2.5, 97.5])

per_config = {}
for cfg in CONFIGS:
    files = sorted(glob.glob(f"{CRAWL}/out_{cfg}_s*.csv"))
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    df = df.drop_duplicates(subset=['website', 'page_type', 'page_url', 'cookie_name'])
    df['category'] = df['cookie_name'].map(namecat).fillna('Unknown')
    df['is_tgt'] = df['category'] == 'Targeting'
    df['is3p_tgt'] = (df['script_is_third_party'] == 'Yes') & df['is_tgt']
    home_sites = set(df[df.page_type == 'home'].website.unique())

    pp = df.groupby(['website', 'page_type', 'page_url']).agg(
        cookies=('cookie_name', 'size'), tgt=('is_tgt', 'sum'), tptgt=('is3p_tgt', 'sum')).reset_index()
    home = pp[pp.page_type == 'home'].groupby('website').agg(
        h_cookies=('cookies', 'mean'), h_tgt=('tgt', 'mean'), h_tptgt=('tptgt', 'mean'))
    inner = pp[pp.page_type == 'inner'].groupby('website').agg(
        i_cookies=('cookies', 'mean'), i_tgt=('tgt', 'mean'), i_tptgt=('tptgt', 'mean'),
        n_inner=('page_url', 'nunique'))
    m = home.join(inner, how='inner').dropna()

    d3 = df[df.is3p_tgt]
    union3p = d3.groupby('website')['cookie_name'].nunique()
    home3p = d3[d3.page_type == 'home'].groupby('website')['cookie_name'].nunique()
    idx = union3p.index.intersection(home3p.index)
    frac_home = (home3p[idx] / union3p[idx])
    add_none = (union3p[idx] == home3p[idx]).mean()

    delta = (m.i_tptgt - m.h_tptgt).values
    lo, hi = boot_ci(delta)
    try: _, pw = wilcoxon(m.h_tptgt, m.i_tptgt)
    except Exception: pw = float('nan')
    per_config[cfg] = dict(home=home, m=m, cover=len(home_sites), n_hi=len(m),
                           mean_inner=m.n_inner.mean(), delta=delta.mean(), lo=lo, hi=hi, pw=pw,
                           home_captures=100*frac_home.mean(), add_none=100*add_none, n_track=len(idx))

    print("="*78)
    print(f"CONFIG: {cfg.upper()}")
    print(f"  coverage: homepage data for {len(home_sites)}/{N_TARGET} = {100*len(home_sites)/N_TARGET:.1f}%")
    print(f"  sites with home AND >=1 inner: {len(m)} (mean inner/site = {m.n_inner.mean():.2f})")
    for col, lab in [('cookies','Total cookies'),('tgt','Targeting'),('tptgt','3rd-party Targeting')]:
        h, i = m[f'h_{col}'], m[f'i_{col}']
        try: _, p = wilcoxon(h, i)
        except Exception: p = float('nan')
        print(f"    {lab:20s}: home mean={h.mean():.2f} med={h.median():.1f} | inner mean={i.mean():.2f} med={i.median():.1f} | Wilcoxon p={p:.3g}")
    print(f"  PAIRED diff (inner - home) 3p-Targeting: {delta.mean():+.2f}  95% CI [{lo:+.2f},{hi:+.2f}]  (Wilcoxon p={pw:.3g})")
    print(f"  HOME captures {100*frac_home.mean():.1f}% of a site's distinct 3p-Targeting trackers; {100*add_none:.0f}% of sites add NONE  (n={len(idx)} sites w/ >=1 tracker)")

print("\n" + "#"*78)
print("CROSS-CONFIG: homepage 3rd-party Targeting cookies vs DEFAULT (paired on common sites)")
base = per_config['default']['home']['h_tptgt']
print(f"  DEFAULT homepage 3p-Targeting: mean={base.mean():.2f} med={base.median():.1f} (n={len(base)})")
rows = []
for cfg in ['gpc', 'dnt', 'block3p']:
    oth = per_config[cfg]['home']['h_tptgt']
    common = base.index.intersection(oth.index)
    b, o = base[common], oth[common]
    try: _, p = wilcoxon(b, o)
    except Exception: p = float('nan')
    red = 100*(1 - o.mean()/b.mean()) if b.mean() else float('nan')
    rows.append(dict(config=cfg, n=len(common), default_mean=b.mean(), cfg_mean=o.mean(),
                     pct_reduction=red, wilcoxon_p=p))
    print(f"  {cfg.upper():9s}: mean={o.mean():.2f} vs default {b.mean():.2f}  => {red:+.1f}% change  (paired Wilcoxon p={p:.3g}, n={len(common)})")

pd.DataFrame(rows).to_csv(f"{BASE}/data/results/inner_allconfigs_crossconfig.csv", index=False)
summ = pd.DataFrame([dict(config=c, coverage=per_config[c]['cover'], sites_home_inner=per_config[c]['n_hi'],
    mean_inner=round(per_config[c]['mean_inner'],2), paired_diff_3ptgt=round(per_config[c]['delta'],2),
    ci_lo=round(per_config[c]['lo'],2), ci_hi=round(per_config[c]['hi'],2), wilcoxon_p=per_config[c]['pw'],
    home_captures_pct=round(per_config[c]['home_captures'],1), sites_add_none_pct=round(per_config[c]['add_none'],0))
    for c in CONFIGS])
summ.to_csv(f"{BASE}/data/results/inner_allconfigs_summary.csv", index=False)
print(f"\nwrote results/inner_allconfigs_summary.csv + inner_allconfigs_crossconfig.csv")
