# Usage: python analyze_ccpa_frame.py  |  Analyze the systematic CCPA-relevant expansion corpus (1,000 US-English Tranco sites).
import glob, json, re, os, numpy as np, pandas as pd
from scipy.stats import wilcoxon
BASE = os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TR = f"{BASE}/data/tranco_audit"
CONFIGS = ['default', 'gpc', 'dnt', 'block3p']
def norm(x): x=re.sub(r'^https?://','',str(x).strip().lower()); return re.sub(r'^www\.','',x).split('/')[0]

ref = pd.read_csv(f"{BASE}/data/final_default_state_comprehensive_reclassified.csv", low_memory=False)
namecat = ref.groupby('cookie_name')['category'].agg(lambda s: s.value_counts().idxmax()).to_dict()

per = {}
for cfg in CONFIGS:
    files = sorted(glob.glob(f"{TR}/out_ccpa_{cfg}_s*.csv"))
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    df = df[df.page_type == 'home'].drop_duplicates(subset=['website','cookie_name','cookie_domain','set_by_script_domain'])
    df['website'] = df['website'].apply(norm)
    df['is3p_tgt'] = (df['script_is_third_party'] == 'Yes') & (df['cookie_name'].map(namecat).fillna('Unknown') == 'Targeting')
    per[cfg] = df.groupby('website')['is3p_tgt'].sum()
    print(f"{cfg:8s}: {df.website.nunique()} sites w/ home data | mean 3p-Targeting={per[cfg].mean():.2f} | track>=1: {100*(per[cfg]>0).mean():.1f}%")

print("\n=== Privacy-signal effect on the label-free corpus (homepage 3p-Targeting vs default) ===")
base = per['default']
for cfg in ['gpc','dnt','block3p']:
    common = base.index.intersection(per[cfg].index); b,o = base[common], per[cfg][common]
    try: _,p = wilcoxon(b,o)
    except Exception: p = float('nan')
    red = 100*(1 - o.mean()/b.mean()) if b.mean() else float('nan')
    print(f"  {cfg.upper():8s}: mean {o.mean():.2f} vs {b.mean():.2f} = {red:+.1f}%  (paired Wilcoxon p={p:.2g}, n={len(common)})")

pol = [json.loads(l) for l in open(f"{TR}/ccpa_policies.jsonl") if l.strip()]
P = {norm(r['domain']): r for r in pol}
usable = sum(1 for r in pol if r.get('policy_status')=='ok')
optout = {d for d,r in P.items() if r.get('ccpa_optout_url')}
print(f"\n=== Policy availability (systematic US-English frame) ===")
print(f"  {len(pol)} sites scraped | usable policy: {usable} ({100*usable/len(pol):.0f}%) | present a CCPA opt-out signal: {len(optout)} ({100*len(optout)/len(pol):.0f}%)")

print("\n=== Compliance CLAIM vs behavior ===")
def tracks(d): return per['default'].get(d,0) > 0
claim = [d for d in optout if d in per['default'].index]
claim_track = [d for d in claim if tracks(d)]
print(f"  sites that present a CCPA opt-out mechanism AND have behavior data: {len(claim)}")
print(f"    ...still set >=1 third-party Targeting cookie at load: {len(claim_track)} = {100*len(claim_track)/len(claim):.1f}%")

red_gpc = [d for d in claim_track if per['gpc'].get(d,0) < per['default'].get(d,0)]
nored_gpc = [d for d in claim_track if per['gpc'].get(d,99) >= per['default'].get(d,0)]
print(f"    of those tracking, under GPC: reduce={len(red_gpc)} ({100*len(red_gpc)/len(claim_track):.0f}%) | NO reduction={len(nored_gpc)} ({100*len(nored_gpc)/len(claim_track):.0f}%)")

rows=[]
for d in sorted(set(per['default'].index) | optout):
    rows.append(dict(domain=d, claims_ccpa_optout=(d in optout), policy_status=P.get(d,{}).get('policy_status',''),
        tp_tgt_default=int(per['default'].get(d,0)), tp_tgt_gpc=int(per['gpc'].get(d,0)),
        tp_tgt_dnt=int(per['dnt'].get(d,0)), tp_tgt_block3p=int(per['block3p'].get(d,0))))
pd.DataFrame(rows).to_csv(f"{BASE}/data/results/ccpa_frame_joined.csv", index=False)
print(f"\nwrote data/results/ccpa_frame_joined.csv ({len(rows)} sites)")
