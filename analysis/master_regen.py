# Usage: python master_regen.py  |  Regenerate the paper's tables/figures on the re-verified label set (OLD-vs-NEW report).
import json, re, csv, numpy as np, pandas as pd
from scipy.stats import mannwhitneyu, chi2_contingency, fisher_exact
from statsmodels.stats.multitest import multipletests
import os
BASE = os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); DATA = f"{BASE}/data"
def norm(x): x=re.sub(r'^https?://','',str(x).strip().lower()); return re.sub(r'^www\.','',x).split('/')[0]

rv = {norm(r['website']): r for r in csv.DictReader(open(f"{BASE}/data/results/subjectivity_apollo_reclassified.csv"))}
SUBJ_OLD = {"subjected","subjected, location","subjected,location"}
old_status = {norm(r['website']): ("Subject" if str(r['ccpa']).strip().lower() in SUBJ_OLD else "Not-Subject")
              for r in csv.DictReader(open(f"{DATA}/data_source.csv"))}
def ocoarse(l):
    l=(l or '').lower()
    if l.startswith('subjected'): return 'Subject to CCPA'
    if 'non' in l and 'profit' in l: return 'Non-Profit'
    if 'gov' in l: return 'Government'
    if 'revenue' in l or 'not_suff' in l: return 'Revenue Not Sufficient'
    return 'Unknown Eligibility'
def gmap(grp):
    return {'subjected':'Subject to CCPA','subjected, location':'Subject to CCPA','revenue_not_suff':'Revenue Not Sufficient',
            'non_profit':'Non-Profit','government':'Government','unknown':'Unknown Eligibility'}.get(grp,'Unknown Eligibility')
final_status, final_group = {}, {}
for d,r in rv.items():
    if r['new_status'] in ('Subject','Not-Subject'):
        final_status[d]=r['new_status']; final_group[d]=gmap(r['new_group'])
    elif ocoarse(r['old_label'])!='Unknown Eligibility':
        final_status[d]=r['old_status']; final_group[d]=ocoarse(r['old_label'])
    else:
        final_status[d]='EXCLUDE'; final_group[d]='EXCLUDE'

FAILED = {'gfycat.com','limelight.com','makeupalley.com','stylebistro.com','cesarsway.com','mygreatlakes.org',
          'studentloans.gov','mysimon.com','airasia.com','myntra.com','ryanair.com','truecar.com'}
seen=[]; _s=set(); old_fine_wc={}
for r in csv.DictReader(open(f"{DATA}/data_source.csv")):
    wc=str(r['website'] or '').replace('\r','').replace('\n','').strip()
    if wc and wc not in _s: _s.add(wc); seen.append(wc); old_fine_wc[wc]=str(r['ccpa']).strip().lower()
ACCESS_WC=[wc for wc in seen if wc not in FAILED]
ACCESS=set(norm(wc) for wc in ACCESS_WC)
def norm_ccpa(v):
    v=(v or '').strip().lower()
    if v=='government': return 'Government'
    if v=='non_profit': return 'Non-Profit'
    if v=='revenue_not_suff': return 'Revenue Not Sufficient'
    if v in ('subjected','subjected, location','subjected,location'): return 'Subject to CCPA'
    return 'Unknown Eligibility'

with open(f"{BASE}/data/results/final_labels.csv",'w',newline='') as f:
    w=csv.writer(f); w.writerow(['website','accessible','old_status','final_status','final_group'])
    for d in sorted(rv): w.writerow([d,('yes' if d in ACCESS else 'no'),old_status.get(d,''),final_status[d],final_group[d]])
print(f"froze final_labels.csv ({len(final_status)} sites) | accessible corpus = {len(ACCESS_WC)} (target 1,002)")

import collections
CATS4=['Government','Non-Profit','Revenue Not Sufficient','Subject to CCPA','Unknown Eligibility']
def newcat(d):
    g=final_group.get(d,'')
    return 'Unknown Eligibility' if g in ('EXCLUDE','') else g
oldc=collections.Counter(norm_ccpa(old_fine_wc[wc]) for wc in ACCESS_WC)
newc=collections.Counter(newcat(norm(wc)) for wc in ACCESS_WC)
print("\n=== TABLE 4 — category counts on the 1,002 accessible (OLD vs NEW) ===")
print(f"  {'category':26s}{'OLD':>6}{'NEW':>6}{'Δ':>6}")
for c in CATS4:
    print(f"  {c:26s}{oldc.get(c,0):>6}{newc.get(c,0):>6}{newc.get(c,0)-oldc.get(c,0):>+6}")
print(f"  {'TOTAL':26s}{sum(oldc.values()):>6}{sum(newc.values()):>6}")
os_=collections.Counter(('Subject' if norm_ccpa(old_fine_wc[wc])=='Subject to CCPA' else 'Not-Subject') for wc in ACCESS_WC)
ns_=collections.Counter(final_status.get(norm(wc),'EXCLUDE') for wc in ACCESS_WC)
print("\n=== §3.1 split (Subject vs Not-Subject) on the 1,002 accessible ===")
print(f"  OLD: Subject {os_['Subject']}  Not-Subject {os_['Not-Subject']}  (total {os_['Subject']+os_['Not-Subject']})")
print(f"  NEW: Subject {ns_['Subject']}  Not-Subject {ns_['Not-Subject']}  (EXCLUDE {ns_['EXCLUDE']}, total {ns_['Subject']+ns_['Not-Subject']})")

POL=json.load(open(f"{DATA}/ccpa_policy_audit_data_source_mapped.json"))
COOK=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",low_memory=False)
COOK["key"]=COOK["website"].apply(norm)
def build_family(label_map):
    def sof(dom):
        l=label_map.get(norm(dom)); return True if l=="Subject" else (False if l=="Not-Subject" else None)
    men=lambda s:not (str(s or "").strip().lower().startswith("not mentioned") or str(s or "").strip().lower() in ("","n/a","none"))
    tf=lambda v: v is True or str(v).lower()=="true"
    rows=[]
    for dom,rec in POL.items():
        s=sof(dom)
        if s is None: continue
        ad=rec["audit_data"]; ra=ad["rubric_assessment"]; dm=ra["disclosure_map"]; bc=ad["behavioral_claims"]
        rows.append(dict(subject=s, completeness=ra.get("completeness_score"), usability=ra.get("usability_score"),
            accuracy=ra.get("accuracy_score"), **{f"d_{k}":bool(v) for k,v in dm.items()},
            honors_gpc=tf(bc.get("honors_gpc")), respects_dnt=tf(bc.get("respects_dnt")),
            sells_data=tf(bc.get("sells_data")), shares_3p=tf(bc.get("shares_with_third_parties")),
            m_online=men(ad.get("online_data_practices")), m_offline=men(ad.get("offline_data_practices"))))
    P=pd.DataFrame(rows); S=P[P.subject]; N=P[~P.subject]; fam=[]
    def add(t,a,b,p,e): fam.append(dict(test=t,subj=a,notsubj=b,p=p,eff=e))
    for nm,c in [("rubric_completeness","completeness"),("rubric_usability","usability"),("rubric_accuracy","accuracy")]:
        a,b=S[c].dropna(),N[c].dropna(); u,p=mannwhitneyu(a,b,alternative="two-sided")
        add(nm,f"med{a.median():.0f}",f"med{b.median():.0f}",p,abs(1-2*u/(len(a)*len(b))))
    def chi(t,col):
        ct=pd.crosstab(P["subject"],P[col])
        if ct.shape!=(2,2): return
        c2,p,_,exp=chi2_contingency(ct,correction=False)
        if (exp<5).any(): _,p=fisher_exact(ct.values)
        add(t,f"{100*P[P.subject][col].mean():.1f}%",f"{100*P[~P.subject][col].mean():.1f}%",p,np.sqrt(c2/ct.values.sum()))
    for c in ["d_data_collected","d_data_shared","d_purpose_of_collection","d_retention_period","d_right_to_access","d_right_to_delete","d_opt_out"]: chi("disc_"+c[2:],c)
    for c in ["honors_gpc","respects_dnt","sells_data","shares_3p","m_online","m_offline"]: chi("claim_"+c,c)
    cf=COOK.copy(); cf["lab"]=cf["key"].map(lambda k:label_map.get(k)); cf=cf[cf["lab"].isin(["Subject","Not-Subject"])].copy()
    cf["subject"]=cf["lab"].eq("Subject"); cf["is3p"]=cf["script_is_third_party"].eq("Yes")
    CATS=["Targeting","Performance","Functional","Necessary"]
    per=cf.groupby(["key","subject","category"]).size().unstack(fill_value=0).reset_index()
    for c in CATS:
        if c not in per.columns: per[c]=0
    Sc,Nc=per[per.subject],per[~per.subject]
    for c in CATS:
        a,b=Sc[c],Nc[c]; u,p=mannwhitneyu(a,b,alternative="two-sided"); add(f"count_{c}",f"med{a.median():.0f}",f"med{b.median():.0f}",p,abs(1-2*u/(len(a)*len(b))))
    def c3(t,sub):
        ct=pd.crosstab(sub["subject"],sub["is3p"])
        if ct.shape!=(2,2): return
        c2,p,_,_=chi2_contingency(ct,correction=False); add(t,f"{100*sub[sub.subject]['is3p'].mean():.1f}%",f"{100*sub[~sub.subject]['is3p'].mean():.1f}%",p,np.sqrt(c2/ct.values.sum()))
    c3("3p_overall",cf)
    for c in CATS: c3(f"3p_{c}",cf[cf.category==c])
    F=pd.DataFrame(fam); F["p_Holm"]=multipletests(F["p"],alpha=0.05,method="holm")[1]; F["sig"]=F["p_Holm"]<0.05
    F["nS"]=len(S); F["nN"]=len(N); return F.set_index("test")

FO=build_family({norm(wc): ('Subject' if norm_ccpa(old_fine_wc[wc])=='Subject to CCPA' else 'Not-Subject') for wc in ACCESS_WC})
FN=build_family({norm(wc): final_status.get(norm(wc),'EXCLUDE') for wc in ACCESS_WC})
print("\n=== 25 SUBJECT-vs-NOT-SUBJECT TESTS (Table 1 policy + Table 2 cookie + MHT) ===")
print(f"  sample: OLD Subj/Not {FO['nS'].iloc[0]}/{FO['nN'].iloc[0]}  |  NEW Subj/Not {FN['nS'].iloc[0]}/{FN['nN'].iloc[0]}")
print(f"  {'test':22s} | {'OLD subj/not':16s} {'Holm':>5} | {'NEW subj/not':16s} {'Holm':>5} | Δsig")
for t in FN.index:
    o=FO.loc[t] if t in FO.index else None; n=FN.loc[t]
    os_s=f"{o['subj']}/{o['notsubj']}" if o is not None else "—"; ns_s=f"{n['subj']}/{n['notsubj']}"
    osig="sig" if (o is not None and o['sig']) else " . "; nsig="sig" if n['sig'] else " . "
    flag="" if (o is not None and o['sig']==n['sig']) else " <-- CHANGED"
    print(f"  {t:22s} | {os_s:16s} {osig:>5} | {ns_s:16s} {nsig:>5} |{flag}")
print(f"\n  Holm-significant: OLD {int(FO['sig'].sum())}/25  ->  NEW {int(FN['sig'].sum())}/25")
print("wrote data/results/final_labels.csv")
