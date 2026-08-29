# Usage: python analyze_inner_full.py  |  Full-run (1,002-site) inner-page vs homepage third-party tracking comparison.
import sys, glob
import pandas as pd, numpy as np

import os
BASE = os.path.join(os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
SHARD_GLOB = sys.argv[1] if len(sys.argv) > 1 else \
    f"{BASE}/inner_page_crawl/clean_run_2026-07-04/inner_s[0-3].csv"
SITES_TXT = sys.argv[2] if len(sys.argv) > 2 else \
    f"{BASE}/inner_page_crawl/full_sites.txt"

rng = np.random.default_rng(20260704)

files = sorted(glob.glob(SHARD_GLOB))
print(f"Shard files: {[f.split('/')[-1] for f in files]}")
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
before = len(df)
df = df.drop_duplicates(subset=['website', 'page_type', 'page_url', 'cookie_name'])
print(f"Rows: {before} -> {len(df)} after dedup | sites={df.website.nunique()} "
      f"| home rows={(df.page_type=='home').sum()} inner rows={(df.page_type=='inner').sum()}")

target_sites = [s.strip() for s in open(SITES_TXT) if s.strip()]
N_TARGET = len(target_sites)

ref = pd.read_csv(f"{BASE}/final_default_state_comprehensive_reclassified.csv", low_memory=False)
namecat = ref.groupby('cookie_name')['category'].agg(lambda s: s.value_counts().idxmax()).to_dict()
df['category'] = df['cookie_name'].map(namecat).fillna('Unknown')
df['is_target'] = df['category'] == 'Targeting'
df['is3p_target'] = (df['script_is_third_party'] == 'Yes') & df['is_target']

statuscol = 'CCPA_Category' if 'CCPA_Category' in ref.columns else 'ccpa'
site_status = ref.groupby('website')[statuscol].agg(lambda s: s.value_counts().idxmax()).to_dict()

home_sites = set(df[df.page_type == 'home'].website.unique())
cov = len(home_sites) / N_TARGET
print("\n" + "="*70)
print(f"COVERAGE: homepage data for {len(home_sites)}/{N_TARGET} sites = {cov*100:.1f}%")
print("(reference: pilot ~92% / prior ~89%)")

pp = df.groupby(['website', 'page_type', 'page_url']).agg(
    cookies=('cookie_name', 'size'),
    targeting=('is_target', 'sum'),
    tp_targeting=('is3p_target', 'sum')).reset_index()
home = pp[pp.page_type == 'home'].groupby('website').agg(
    h_cookies=('cookies', 'mean'), h_tgt=('targeting', 'mean'), h_tptgt=('tp_targeting', 'mean'))
inner = pp[pp.page_type == 'inner'].groupby('website').agg(
    i_cookies=('cookies', 'mean'), i_tgt=('targeting', 'mean'),
    i_tptgt=('tp_targeting', 'mean'), n_inner=('page_url', 'nunique'))
m = home.join(inner, how='inner').dropna()
print(f"\nSites with homepage AND >=1 inner page: {len(m)} "
      f"(mean inner pages/site = {m.n_inner.mean():.2f})")

from scipy.stats import wilcoxon
print("\n=== Homepage vs Inner-page (per-site means) ===")
for col, lab in [('cookies', 'Total cookies'), ('tgt', 'Targeting'), ('tptgt', '3rd-party Targeting')]:
    h, i = m[f'h_{col}'], m[f'i_{col}']
    try: _, p = wilcoxon(h, i)
    except Exception: p = float('nan')
    print(f"{lab:22s}: home mean={h.mean():.2f} med={h.median():.1f} | "
          f"inner mean={i.mean():.2f} med={i.median():.1f} | Wilcoxon p={p:.3g} "
          f"| inner>=home {100*(i>=h).mean():.0f}%")

delta = (m.i_tptgt - m.h_tptgt).values
boot = np.array([rng.choice(delta, size=len(delta), replace=True).mean() for _ in range(10000)])
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"\nPaired mean diff (inner - home) 3p-Targeting: {delta.mean():+.2f}  "
      f"95% CI [{lo:+.2f}, {hi:+.2f}]")

d3 = df[df.is3p_target]
union3p = d3.groupby('website')['cookie_name'].nunique()
home3p = d3[d3.page_type == 'home'].groupby('website')['cookie_name'].nunique()
common = union3p.index.intersection(home3p.index)
u, ho = union3p.reindex(common).fillna(0), home3p.reindex(common).fillna(0)
capture = ho.sum() / u.sum() if u.sum() else float('nan')
growth = (u.sum() - ho.sum()) / ho.sum() if ho.sum() else float('nan')
add_none = (u <= ho).mean()
print(f"\nDistinct 3p-Targeting trackers (sites with >=1): {len(common)} sites")
print(f"  home-only total={int(ho.sum())}  home+inner union total={int(u.sum())}")
print(f"  homepage CAPTURES {capture*100:.1f}% of distinct trackers "
      f"(inner adds {growth*100:.1f}%)")
print(f"  sites adding NO new distinct 3p-Targeting tracker: {add_none*100:.0f}%")

print("\n=== 3p-Targeting home-vs-inner by CCPA status ===")
m2 = m.copy()
m2['status'] = [str(site_status.get(w, 'unknown')).lower() for w in m2.index]
def bucket(s):
    if 'not' in s or 'non' in s: return 'not-subject'
    if 'subject' in s or s in ('yes', 'true', '1'): return 'subject'
    return 'other/unknown'
m2['bucket'] = m2['status'].map(bucket)
for b in ['subject', 'not-subject', 'other/unknown']:
    sub = m2[m2.bucket == b]
    if len(sub) < 3:
        print(f"{b:14s}: n={len(sub)} (too few)"); continue
    try: _, p = wilcoxon(sub.h_tptgt, sub.i_tptgt)
    except Exception: p = float('nan')
    print(f"{b:14s}: n={len(sub)} | home mean 3pT={sub.h_tptgt.mean():.2f} "
          f"inner={sub.i_tptgt.mean():.2f} | Wilcoxon p={p:.3g}")

out = f"{BASE}/results/inner_vs_home_full.csv"
m.to_csv(out)
print(f"\nSaved per-site table -> {out}")
print("VERDICT: homepage-only is representative iff capture ~>=89% and paired diff <=0 / CI excludes large positive.")
