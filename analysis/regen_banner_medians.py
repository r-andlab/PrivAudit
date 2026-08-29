# Usage: python regen_banner_medians.py  |  Reproduce the section 4.2 consent-flow banner cookie medians on the re-verified labels.
import re, csv, numpy as np, pandas as pd
import os
BASE=os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); DATA=f"{BASE}/data"
def norm(x): x=re.sub(r'^https?://','',str(x).strip().lower()); return re.sub(r'^www\.','',x).split('/')[0]
rv={norm(r['website']):r for r in csv.DictReader(open(f"{BASE}/data/results/subjectivity_apollo_reclassified.csv"))}
FINAL={}
for d,r in rv.items():
    if r['new_status'] in ('Subject','Not-Subject'): FINAL[d]=r['new_status']
    elif (r['old_label'] or '').lower() not in ('unknown','',): FINAL[d]=r['old_status']
    else: FINAL[d]='EXCLUDE'
def newlab(dom): return FINAL.get(norm(dom))

WEB="website"; STAGES={"Initial":"initial_cookies","Accept":"consent_accept","Reject":"consent_reject"}
ban=pd.read_csv(f"{DATA}/cookie_data_final - Banner_present.csv",dtype=str)
comp=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",dtype=str,low_memory=False)

site_ccpa_old={}
for w,c in comp.groupby(WEB)['CCPA_Category'].first().items():
    site_ccpa_old[w]='Subject' if str(c).strip()=='Subject to CCPA' else 'Not-Subject'
def present_mask(s): s=s.astype(str).str.strip().str.lower(); return ~s.isin(["","nan","none"])
def per_site(dfg,col): d=dfg.loc[present_mask(dfg[col]),[WEB,col]]; return d.groupby(WEB).size().astype(int)
def grp_old(w): return site_ccpa_old.get(w)
def grp_new(w):

    if w not in site_ccpa_old: return None
    l=newlab(w); return l if l in ('Subject','Not-Subject') else None

def run(groupfn,tag):
    ban2=ban.copy(); ban2['G']=ban2[WEB].map(groupfn)
    print(f"\n== {tag} ==")
    for g in ['Subject','Not-Subject']:
        sites=ban2[ban2['G']==g][WEB].unique(); dfg=ban2[ban2[WEB].isin(sites)]
        n=len(sites); meds={}
        for name,col in STAGES.items():
            cnt=per_site(dfg,col).reindex(sites,fill_value=0); meds[name]=int(np.median(cnt))
        print(f"  {g:12s} N={n:3d}  Initial {meds['Initial']}  Accept {meds['Accept']}  Reject {meds['Reject']}")
run(grp_old,"OLD (comprehensive CCPA_Category)")
run(grp_new,"NEW (frozen labels)")
print("\n(Paper OLD: Subject 24/27/22 N=174 ; Not-Subject 16/18/17 N=65.)")
