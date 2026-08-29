# Usage: python regen_policy_stats.py  |  Recompute the section 4.1 derived policy statistics on the re-verified labels.
import json, csv, re
from scipy.stats import mannwhitneyu, chi2_contingency
import numpy as np
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
audit=json.load(open(f"{DATA}/ccpa_policy_audit_data_source_mapped.json"))
w2c={str(r['website']).strip().lower():str(r['ccpa']) for r in csv.DictReader(open(f"{DATA}/data_source.csv"))}
def oldcat(w):
    c=w2c.get(str(w).strip().lower()); return 'Subject' if (c is not None and 'subjected' in str(c).lower()) else 'Not-Subject'
def newcat(w):
    l=newlab(w); return l if l in ('Subject','Not-Subject') else None

def gather(catfn):
    S={'rub':{'c':[],'u':[],'a':[]},'disc':{},'claimT':{},'ment':{'online':0,'offline':0,'cookies':0},'dntF':0,'n':0}
    N={'rub':{'c':[],'u':[],'a':[]},'disc':{},'claimT':{},'ment':{'online':0,'offline':0,'cookies':0},'dntF':0,'n':0}
    DK=['data_collected','data_shared','opt_out','purpose_of_collection','retention_period','right_to_access','right_to_delete']
    CK=['sells_data','honors_gpc']
    for g in (S,N):
        for k in DK: g['disc'][k]=[0,0]
        for k in CK: g['claimT'][k]=[0,0]
    for w,rec in audit.items():
        cat=catfn(w)
        if cat not in ('Subject','Not-Subject'): continue
        g=S if cat=='Subject' else N; g['n']+=1
        ad=rec.get('audit_data',{}); ra=ad.get('rubric_assessment',{}); dm=ra.get('disclosure_map',{}); bc=ad.get('behavioral_claims',{})
        for key,acc in (('completeness_score','c'),('usability_score','u'),('accuracy_score','a')):
            v=ra.get(key)
            if v is not None: g['rub'][acc].append(v)
        for k in DK:
            g['disc'][k][1]+=1
            if dm.get(k) is True: g['disc'][k][0]+=1
        for k in CK:
            g['claimT'][k][1]+=1
            v=bc.get(k)
            if v is True or str(v).lower()=='true': g['claimT'][k][0]+=1
        on=(ad.get('online_data_practices','') or ''); off=(ad.get('offline_data_practices','') or '')
        if 'cookie' in on.lower(): g['ment']['cookies']+=1
        if on and len(on.strip())>20: g['ment']['online']+=1
        if off and len(off.strip())>20: g['ment']['offline']+=1
        if str(bc.get('respects_dnt')).lower()=='false' or bc.get('respects_dnt') is False: g['dntF']+=1
    return S,N

def cramers_v(a,b,c,d):
    tab=[[a,b],[c,d]]; chi2,p,_,_=chi2_contingency(tab); n=a+b+c+d
    return (chi2/n)**0.5, p
def rbc(x,y):
    U,p=mannwhitneyu(x,y,alternative='two-sided'); r=1-2*U/(len(x)*len(y)); return abs(r),p

def report(tag,S,N):
    print(f"\n===== {tag}  (Subj n={S['n']} / Not n={N['n']}) =====")
    for nm,acc in (('completeness','c'),('usability','u'),('accuracy','a')):
        r,p=rbc(S['rub'][acc],N['rub'][acc]); print(f"  rubric {nm:12s} r={r:.2f} (med S {int(np.median(S['rub'][acc]))}/N {int(np.median(N['rub'][acc]))})")
    def V(key,src='disc'):
        st,nt=S[src][key],N[src][key]
        v,p=cramers_v(st[0],st[1]-st[0],nt[0],nt[1]-nt[0]); return v,p,100*st[0]/st[1],100*nt[0]/nt[1]
    for k,lab in (('right_to_access','access'),('right_to_delete','delete'),('opt_out','opt-out'),('retention_period','retention')):
        v,p,ps,pn=V(k); print(f"  {lab:10s} {ps:.1f} vs {pn:.1f}  V={v:.02f} p={p:.1e}")
    v,p,ps,pn=V('sells_data','claimT'); print(f"  sells      {ps:.1f} vs {pn:.1f}  V={v:.02f} p={p:.3f}")
    v,p,ps,pn=V('honors_gpc','claimT'); print(f"  GPC        {ps:.1f} vs {pn:.1f}  V={v:.02f} p={p:.1e}")
    tot=S['n']+N['n']
    for m in ('online','cookies','offline'):
        ov=100*(S['ment'][m]+N['ment'][m])/tot; print(f"  overall {m:8s} {ov:.1f}%")
    print(f"  DNT not-honoring overall {100*(S['dntF']+N['dntF'])/tot:.1f}%")
    print(f"  Not missed access {100-100*N['disc']['right_to_access'][0]/N['disc']['right_to_access'][1]:.1f}% / delete {100-100*N['disc']['right_to_delete'][0]/N['disc']['right_to_delete'][1]:.1f}% | lacked opt-out {100-100*N['disc']['opt_out'][0]/N['disc']['opt_out'][1]:.1f}%")

So,No=gather(oldcat); report("OLD (verify: r .27/.31/.25; access V.15 delete .17 optout .19 retention .13; sells .08 p.009; GPC .17; online 93.2 cookies 86.0 offline 26.0; DNT 31.6; missed ~29/lacked ~40)",So,No)
Sn,Nn=gather(newcat); report("NEW",Sn,Nn)
