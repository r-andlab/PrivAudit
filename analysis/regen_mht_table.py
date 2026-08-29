# Usage: python regen_mht_table.py  |  Reproduce the appendix multiple-hypothesis-correction table (BH + Holm) on the re-verified labels.
import json, csv, re, numpy as np, pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu
from statsmodels.stats.multitest import multipletests
import os
BASE=os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); DATA=f"{BASE}/data"
def norm(x): x=re.sub(r'^https?://','',str(x).strip().lower()); return re.sub(r'^www\.','',x).split('/')[0]
EXC={'conservativetribune.com','findsimilar.com','futurescopes.com','ww2aircraft.net'}
rv={norm(r['website']):r for r in csv.DictReader(open(f"{BASE}/data/results/subjectivity_apollo_reclassified.csv"))}
FINAL={}
for d,r in rv.items():
    if r['new_status'] in ('Subject','Not-Subject'): FINAL[d]=r['new_status']
    elif (r['old_label'] or '').lower() not in ('unknown','',): FINAL[d]=r['old_status']
    else: FINAL[d]='EXCLUDE'
def newlab(d): return FINAL.get(norm(d))
audit=json.load(open(f"{DATA}/ccpa_policy_audit_data_source_mapped.json"))
w2c={str(r['website']).strip().lower():str(r['ccpa']) for r in csv.DictReader(open(f"{DATA}/data_source.csv"))}
def polcat_old(w):
    c=w2c.get(str(w).strip().lower()); return 'Subject' if (c is not None and 'subjected' in str(c).lower()) else 'Not-Subject'
def polcat_new(w):
    l=newlab(w); return l if l in ('Subject','Not-Subject') else None
ck=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",dtype=str,low_memory=False)
ck['nw']=ck['website'].apply(norm)
ck['is3p']=ck['script_is_third_party'].fillna('No').astype(str).str.strip().eq('Yes')
def catn(v):
    k=str(v).strip().lower()
    if k in ('targeting','advertisement','targeting cookies'): return 'Targeting'
    if 'performance' in k: return 'Performance'
    if 'functional' in k: return 'Functional'
    if k in ('strictly necessary','necessary','strictly necessary cookies'): return 'Necessary'
    return 'Unknown'
ck['ct']=ck['category'].apply(catn)
def pres(c): return ck[c].notna()&(ck[c].astype(str).str.strip()!='')
ck['pdef']=pres('initial_cookies')
ck['old_g']=ck['CCPA_Category'].apply(lambda v:'Subject' if str(v).strip()=='Subject to CCPA' else 'Not-Subject')
ck['new_g']=ck['nw'].apply(lambda w: newlab(w) if newlab(w) in ('Subject','Not-Subject') else 'EXCLUDE')

def chi2p(a,b,c,d):
    try: return chi2_contingency([[a,b],[c,d]],correction=False)[1]
    except: return 1.0

def policy_tests(catfn):
    S={'n':0}; N={'n':0}
    DK=['data_collected','data_shared','opt_out','purpose_of_collection','retention_period','right_to_access','right_to_delete']
    CK=['sells_data','honors_gpc','respects_dnt','shares_with_third_parties']
    rub={'Subject':{'c':[],'u':[],'a':[]},'Not-Subject':{'c':[],'u':[],'a':[]}}
    cnt={'Subject':{k:0 for k in DK+CK+['m_online','m_offline']},'Not-Subject':{k:0 for k in DK+CK+['m_online','m_offline']}}
    tot={'Subject':0,'Not-Subject':0}
    for w,rec in audit.items():
        g=catfn(w)
        if g not in ('Subject','Not-Subject'): continue
        tot[g]+=1; ad=rec.get('audit_data',{}); ra=ad.get('rubric_assessment',{}); dm=ra.get('disclosure_map',{}); bc=ad.get('behavioral_claims',{})
        for key,acc in (('completeness_score','c'),('usability_score','u'),('accuracy_score','a')):
            if ra.get(key) is not None: rub[g][acc].append(ra[key])
        for k in DK:
            if dm.get(k) is True: cnt[g][k]+=1
        for k in CK:
            v=bc.get(k)
            if v is True or str(v).lower()=='true': cnt[g][k]+=1
        on=(ad.get('online_data_practices','') or ''); off=(ad.get('offline_data_practices','') or '')
        if on and len(on.strip())>20: cnt[g]['m_online']+=1
        if off and len(off.strip())>20: cnt[g]['m_offline']+=1
    res={}
    for k in DK: res['disc_'+k]=chi2p(cnt['Subject'][k],tot['Subject']-cnt['Subject'][k],cnt['Not-Subject'][k],tot['Not-Subject']-cnt['Not-Subject'][k])
    for k in ['sells_data','honors_gpc','respects_dnt']: res['claim_'+({'sells_data':'sells_data','honors_gpc':'honors_gpc','respects_dnt':'respects_dnt'}[k])]=chi2p(cnt['Subject'][k],tot['Subject']-cnt['Subject'][k],cnt['Not-Subject'][k],tot['Not-Subject']-cnt['Not-Subject'][k])
    res['claim_shares_3p']=chi2p(cnt['Subject']['shares_with_third_parties'],tot['Subject']-cnt['Subject']['shares_with_third_parties'],cnt['Not-Subject']['shares_with_third_parties'],tot['Not-Subject']-cnt['Not-Subject']['shares_with_third_parties'])
    for m in ['m_online','m_offline']: res['claim_'+m]=chi2p(cnt['Subject'][m],tot['Subject']-cnt['Subject'][m],cnt['Not-Subject'][m],tot['Not-Subject']-cnt['Not-Subject'][m])
    for nm,acc in (('rubric_completeness','c'),('rubric_usability','u'),('rubric_accuracy','a')):
        res[nm]=mannwhitneyu(rub['Subject'][acc],rub['Not-Subject'][acc],alternative='two-sided')[1]
    return res

def cookie_tests(gcol,drop=False):
    d=ck[~ck['nw'].isin(EXC)] if drop else ck
    res={}
    for cat in ['Targeting','Performance','Functional','Necessary']:
        sub=d[d.ct==cat]; S=sub[sub[gcol]=='Subject']; N=sub[sub[gcol]=='Not-Subject']
        res['3p_'+cat]=chi2p(int(S['is3p'].sum()),int((~S['is3p']).sum()),int(N['is3p'].sum()),int((~N['is3p']).sum()))
    S=d[d[gcol]=='Subject']; N=d[d[gcol]=='Not-Subject']
    res['3p_overall']=chi2p(int(S['is3p'].sum()),int((~S['is3p']).sum()),int(N['is3p'].sum()),int((~N['is3p']).sum()))

    for cat in ['Targeting','Performance','Functional','Necessary']:
        m=d.ct.eq(cat)&d.pdef
        def per(g):
            sites=d[d[gcol]==g]['nw'].unique()
            c=d[m&(d[gcol]==g)].groupby('nw').size().reindex(sites,fill_value=0); return c.values
        res['count_'+cat]=mannwhitneyu(per('Subject'),per('Not-Subject'),alternative='two-sided')[1]
    return res

def full(polfn,ckcol,drop=False):
    r={**{'policy '+k:v for k,v in policy_tests(polfn).items()},**{'cookie '+k:v for k,v in cookie_tests(ckcol,drop).items()}}
    names=list(r.keys()); praw=np.array([r[n] for n in names])
    bh=multipletests(praw,method='fdr_bh')[1]; holm=multipletests(praw,method='holm')[1]
    out=[]
    for i,n in enumerate(names): out.append((n,praw[i],bh[i],holm[i],bh[i]<0.05,holm[i]<0.05))
    out.sort(key=lambda x:x[1])
    return out

def show(tag,out):
    print(f"\n===== {tag} =====  (Holm-sig: {sum(1 for o in out if o[5])}/25)")
    for n,p,bh,ho,bhs,hos in out:
        print(f"  {n:32s} raw={p:.2e} BH={bh:.2e} Holm={ho:.2e} {'BHok' if bhs else '  --'} {'HOLMok' if hos else '  --'}")
import math
def fmt(p):
    if p>=0.001: return f"{p:.3f}"
    e=math.floor(math.log10(p)); m=p/10**e
    return f"${m:.1f}\\times10^{{{e}}}$"
def latex(out):
    print("\n%%%% NEW MHT TABLE ROWS %%%%")
    for n,p,bh,ho,bhs,hos in out:
        fam,test=n.split(' ',1); test=test.replace('_','\\_')
        bhc='\\checkmark' if bhs else '--'; hoc='\\checkmark' if hos else '--'
        print(f"{fam} & {test} & {fmt(p)} & {fmt(bh)} & {fmt(ho)} & {bhc} & {hoc} \\\\")
    print(f"%% Holm-sig {sum(1 for o in out if o[5])}/25 ; BH-sig {sum(1 for o in out if o[4])}/25")
show("OLD (verify: m_offline 2.1e-16, sells raw 0.009 Holm 0.098 --, 3p_Targeting 7.6e-33, count_Targeting 0.848)",full(polcat_old,'old_g'))
NEW=full(polcat_new,'new_g',drop=True)
show("NEW (4 deleted; new labels)",NEW)
latex(NEW)
