# Usage: python size_control_analysis.py  |  Control the disclosure gap for firm size and ad-revenue reliance.
import re, json, pandas as pd, numpy as np
import statsmodels.api as sm
from scipy.stats import chi2_contingency
import os
BASE=os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); DATA=f"{BASE}/data"
def norm(x): x=re.sub(r'^https?://','',str(x).strip().lower()); return re.sub(r'^www\.','',x).split('/')[0]
rc=pd.read_csv(f"{BASE}/data/results/subjectivity_apollo_reclassified.csv",dtype=str)
rc['nw']=rc['website'].apply(norm); rc['rev']=pd.to_numeric(rc['revenue'],errors='coerce')
def newlab(r):
    if r['new_status'] in ('Subject','Not-Subject'): return r['new_status']
    if str(r['old_label']).lower() not in ('unknown','','nan'): return r['old_status']
    return 'EXCLUDE'
rc['grp']=rc.apply(newlab,axis=1)
lab=dict(zip(rc.nw,rc.grp)); rev=dict(zip(rc.nw,rc.rev))

ck=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",dtype=str,low_memory=False); ck['nw']=ck['website'].apply(norm)
tp=ck[(ck['category'].astype(str).str.strip().str.lower().isin(['targeting','advertisement','targeting cookies']))
      &(ck['script_is_third_party'].fillna('No').astype(str).str.strip().eq('Yes'))]
tpc=tp.groupby('nw').size().to_dict()
audit=json.load(open(f"{DATA}/ccpa_policy_audit_data_source_mapped.json"))
rows=[]
for w,rec in audit.items():
    nw=norm(w); g=lab.get(nw)
    if g not in ('Subject','Not-Subject'): continue
    dm=rec.get('audit_data',{}).get('rubric_assessment',{}).get('disclosure_map',{})
    bc=rec.get('audit_data',{}).get('behavioral_claims',{})
    rows.append(dict(nw=nw, subject=1 if g=='Subject' else 0, rev=rev.get(nw),
        adrel=np.log10(tpc.get(nw,0)+1),
        opt_out=int(bool(dm.get('opt_out'))), access=int(bool(dm.get('right_to_access'))),
        delete=int(bool(dm.get('right_to_delete'))),
        gpc=int(str(bc.get('honors_gpc')).lower()=='true')))
df=pd.DataFrame(rows); df['lrev']=np.log10(df['rev']); d=df.dropna(subset=['lrev']).copy()
print(f"N with revenue = {len(d)} (Subject {d.subject.sum()}, Not {len(d)-d.subject.sum()}); "
      f"median rev Subject ${d[d.subject==1].rev.median()/1e6:.0f}M vs Not ${d[d.subject==0].rev.median()/1e6:.0f}M")
print("\n(1) Logistic: outcome ~ subject + log10(revenue) + ad-reliance")
for y in ['opt_out','access','delete']:
    m=sm.Logit(d[y],sm.add_constant(d[['subject','lrev','adrel']])).fit(disp=0)
    print(f"  {y:8s}: subject {m.params['subject']:+.2f} (p={m.pvalues['subject']:.3f}) | "
          f"lrev {m.params['lrev']:+.2f} (p={m.pvalues['lrev']:.3f}) | adrel {m.params['adrel']:+.2f} (p={m.pvalues['adrel']:.3f})")
print("\n(2) Large-only (revenue >= $25M): Subject vs large-but-exempt (nonprofit/government)")
big=d[d.rev>=25e6]
print(f"  large N={len(big)} (Subject {big.subject.sum()}, Not {len(big)-big.subject.sum()})")
for y in ['opt_out','access','delete','gpc']:
    s=100*big[big.subject==1][y].mean(); n=100*big[big.subject==0][y].mean()
    tab=[[big[big.subject==1][y].sum(),(1-big[big.subject==1][y]).sum()],
         [big[big.subject==0][y].sum(),(1-big[big.subject==0][y]).sum()]]
    p=chi2_contingency(tab,correction=False)[1]
    print(f"  {y:8s}: Subject {s:.0f}% vs exempt {n:.0f}% (p={p:.3f})")
