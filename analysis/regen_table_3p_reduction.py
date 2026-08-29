# Usage: python regen_table_3p_reduction.py  |  Reproduce the per-config third-party cookie reduction percentages on the re-verified labels.
import re, csv, pandas as pd
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

df=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",dtype=str,low_memory=False)
def etld(d):
    if pd.isna(d) or str(d)=='' : return None
    p=str(d).lstrip('.').split('.')
    return '.'.join(p[-2:]) if len(p)>=2 else str(d)
df['w_etld']=df['website'].apply(etld); df['c_etld']=df['domain'].apply(etld)
df['is3p_d']=(df['c_etld'].notna()&df['w_etld'].notna()&(df['c_etld']!=df['w_etld']))
df['is3p_s']=df['script_is_third_party'].eq('Yes')
df['is3p']=df['is3p_s']|df['is3p_d']
def cat(v):
    k=str(v).strip().lower()
    if k in ('targeting','advertisement','targeting cookies'): return 'Targeting'
    if k=='performance' or 'performance' in k: return 'Performance'
    if k=='functional' or 'functional' in k: return 'Functional'
    if k in ('strictly necessary','necessary','strictly necessary cookies'): return 'Strictly Necessary'
    return 'Unknown'
df['ct']=df['category'].apply(cat)
def pres(c): return df[c].notna() & (df[c].astype(str).str.strip()!='')
df['pdef']=pres('initial_cookies'); df['pgpc']=pres('gpc_enabled'); df['publ']=pres('ublock')
df['old_g']=df['CCPA_Category'].apply(lambda v:'Subject' if str(v).strip()=='Subject to CCPA' else 'Not-Subject')
df['new_g']=df['website'].apply(newlab)

def red3(mask, cfgcol):
    sub=df[mask & df['is3p']]
    dk=set(map(tuple, sub[sub['pdef']][['website','cookie_name']].values))
    gk=set(map(tuple, sub[sub[cfgcol]][['website','cookie_name']].values))
    if not dk: return None
    persist=len(dk & gk)
    return round(100*(1-persist/len(dk)))
def redT(mask, cfgcol):
    d=int((mask & df['pdef']).sum()); c=int((mask & df[cfgcol]).sum())
    return round(100*(1-c/d)) if d else None

def block(gcol, tag):
    print(f"\n===== {tag} (group col={gcol}) =====")
    for g in ['Subject','Not-Subject']:
        gm=df[gcol].eq(g)
        print(f"  -- {g} --")
        for c in ['Targeting','Performance','Functional','Strictly Necessary','Unknown']:
            m=gm & df['ct'].eq(c)
            print(f"    {c:20s} GPC {redT(m,'pgpc')}({red3(m,'pgpc')})   uBlock {redT(m,'publ')}({red3(m,'publ')})")
        print(f"    {'SUBTOTAL':20s} GPC {redT(gm,'pgpc')}({red3(gm,'pgpc')})   uBlock {redT(gm,'publ')}({red3(gm,'publ')})")
print("TABLE TARGETS (OLD): Subject subtotal GPC 45(37) uBlock 67(82); Targeting 51(41).")
print("                     Not-Subj subtotal GPC 57(31) uBlock 86(89); Targeting 60(34/25?).")
block('old_g','OLD (CCPA_Category)')
block('new_g','NEW (frozen labels)')
