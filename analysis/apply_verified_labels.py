# Usage: python apply_verified_labels.py  |  Write the re-verified CCPA labels (final_labels.csv) onto the cookie dataset's CCPA_Category column and drop the 4 excluded sites, producing the NEW-label file the figure scripts read.
import os, csv, re
import pandas as pd
BASE = os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def norm(d):
    d = re.sub(r'^https?://', '', str(d or '').strip().lower())
    return re.sub(r'^www\.', '', d).split('/')[0]
FINAL = {}
for r in csv.DictReader(open(f"{BASE}/data/results/final_labels.csv")):
    if r['final_status'] in ('Subject', 'Not-Subject'):
        FINAL[norm(r['website'])] = r['final_group']
df = pd.read_csv(f"{BASE}/data/final_default_state_comprehensive_reclassified.csv", dtype=str, low_memory=False)
df['_w'] = df['website'].map(norm)
before = df['website'].nunique()
df = df[df['_w'].isin(FINAL)].copy()
df['CCPA_Category'] = df['_w'].map(FINAL)
out = f"{BASE}/data/final_default_state_comprehensive_NEWLABELS.csv"
df.drop(columns=['_w']).to_csv(out, index=False)
sub = df.groupby('website')['CCPA_Category'].first()
print(f"cookie sites {before} -> {df['website'].nunique()} | Subject {(sub=='Subject to CCPA').sum()} / Not-Subject {(sub!='Subject to CCPA').sum()}")
print(f"wrote {out}")
