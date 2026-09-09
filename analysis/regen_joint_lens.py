# Usage: python regen_joint_lens.py  |  Reproduce the section 4.3 joint-lens (disclosure vs behavior) numbers on the re-verified labels.
import json, csv, re, collections, pandas as pd
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
SUBJ={'subjected','subjected, location','subjected,location'}
subj_ds={norm(r['website']):(r['ccpa'] or '').strip() for r in csv.DictReader(open(f"{DATA}/data_source.csv"))}

pol={}
for dom,rec in audit.items():
    ad=rec.get('audit_data',{}); bc=ad.get('behavioral_claims',{}); dm=ad.get('rubric_assessment',{}).get('disclosure_map',{})
    pol[norm(dom)]={'gpc':bc.get('honors_gpc'),'sells':bc.get('sells_data'),'shares':bc.get('shares_with_third_parties'),
                    'data_shared':dm.get('data_shared'),'data_collected':dm.get('data_collected')}

ck=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",dtype=str,low_memory=False)
ck['nw']=ck['website'].apply(norm)
tgt=ck['category'].astype(str).str.strip().str.lower().isin(['targeting','advertisement','targeting cookies'])
s3=ck['script_is_third_party'].fillna('No').astype(str).str.strip().eq('Yes')
def pres(c): return ck[c].notna()&(ck[c].astype(str).str.strip()!='')
pdef=pres('initial_cookies'); pgpc=pres('gpc_enabled')
def counts(mask): return ck[mask].groupby('nw').size()
tgt_def=counts(tgt&pdef); tgt_gpc=counts(tgt&pgpc)
tp_def=counts(tgt&s3&pdef); tp_gpc=counts(tgt&s3&pgpc)
has_cookie=set(ck['nw'].unique())
sets3pt={w for w in has_cookie if tp_def.get(w,0)>0}

def is_subj_old(w): return subj_ds.get(w) in SUBJ
def is_subj_new(w): return newlab(w)=='Subject'

def report(is_subj,tag,drop_exc=False):
    subj=[w for w in pol if is_subj(w) and (not drop_exc or w not in EXC)]
    print(f"\n===== {tag}: {len(subj)} subject policies =====")

    gpc_claim=[w for w in subj if str(pol[w]['gpc']).lower()=='true' or pol[w]['gpc'] is True]
    matched=[w for w in gpc_claim if w in has_cookie]
    tgtdef=[w for w in matched if tgt_def.get(w,0)>0]      # baseline: set Targeting in Default (denominator for GPC reduction)
    def red(w,d,g): dv=d.get(w,0); gv=g.get(w,0); return (dv-gv)/dv if dv else None
    lt20=[w for w in tgtdef if (red(w,tgt_def,tgt_gpc) or 0)<0.20]
    no_red=[w for w in tgtdef if (red(w,tgt_def,tgt_gpc) or 0)<=0]
    both3p=[w for w in matched if tp_def.get(w,0)>0 and tp_gpc.get(w,0)>0]      # 3p Targeting present in both configs (paper denominator)
    lt20_3p=[w for w in both3p if (red(w,tp_def,tp_gpc) or 0)<0.20]
    nored_3p=[w for w in both3p if (red(w,tp_def,tp_gpc) or 0)<=0]
    n=len(tgtdef) or 1; n3=len(both3p) or 1
    print(f"  GPC: claim honor {len(gpc_claim)} | matched cookie {len(matched)} | set Tgt in Default {len(tgtdef)}")
    print(f"       <20% reduction {len(lt20)} ({100*len(lt20)/n:.1f}%) | no reduction {len(no_red)} ({100*len(no_red)/n:.1f}%)")
    print(f"       3p-Tgt both {len(both3p)}: <20% {len(lt20_3p)} ({100*len(lt20_3p)/n3:.1f}%) | no reduction {len(nored_3p)} ({100*len(nored_3p)/n3:.1f}%)")

    dns=[w for w in subj if pol[w]['sells'] is False]
    dns_cookie=[w for w in dns if w in has_cookie]
    dns_track=[w for w in dns_cookie if w in sets3pt]
    dns_5plus=[w for w in dns_cookie if tp_def.get(w,0)>=5]
    print(f"  DO-NOT-SELL: {len(dns)} ({100*len(dns)/len(subj):.1f}%) | w/ cookie {len(dns_cookie)} | track 3p {len(dns_track)} ({100*len(dns_track)/(len(dns_cookie) or 1):.1f}%) | 5+ {len(dns_5plus)} ({100*len(dns_5plus)/(len(dns_cookie) or 1):.1f}%)")

    setters=[w for w in subj if w in has_cookie and w in sets3pt]
    no_collect=[w for w in setters if pol[w]['data_collected'] is not True]
    neither=[w for w in setters if pol[w]['sells']=='unspecified' and pol[w]['shares']=='unspecified' and pol[w]['data_shared'] is not True]
    ns=len(setters) or 1
    print(f"  SETTERS (3p-Tgt): {len(setters)} | no data_collected disc {len(no_collect)} ({100*len(no_collect)/ns:.1f}%) | silent sale+share {len(neither)} ({100*len(neither)/ns:.1f}%)")

report(is_subj_old,"OLD (verify: GPC claim 146, matched 136, both 94, <20% 45/47.9, nored 34/36.2, 3p<20 59.7, 3p-nored 43.3; DNS 185/35.6, cookie 171, track 90/52.6, 5+ 43/25.1; setters 246, nocol 26/10.6, neither 21/8.5)")
report(is_subj_new,"NEW",drop_exc=True)
