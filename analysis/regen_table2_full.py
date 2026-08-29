# Usage: python regen_table2_full.py  |  Reproduce Table 2 (third-party comprehensive) on the re-verified labels.
import re, csv, pandas as pd
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
df=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",dtype=str,low_memory=False)
df['nw']=df['website'].apply(norm)
def catn(v):
    k=str(v).strip().lower()
    if k in ('targeting','advertisement','targeting cookies'): return 'Targeting'
    if 'performance' in k: return 'Performance'
    if 'functional' in k: return 'Functional'
    if k in ('strictly necessary','necessary','strictly necessary cookies'): return 'Strictly Necessary'
    return 'Unknown'
df['ct']=df['category'].apply(catn)
def etld(d):
    if pd.isna(d) or str(d)=='' : return None
    p=str(d).lstrip('.').split('.'); return '.'.join(p[-2:]) if len(p)>=2 else str(d)
df['s3']=df['script_is_third_party'].fillna('No').astype(str).str.strip().eq('Yes')
df['d3']=(df['domain'].apply(etld).notna()&df['website'].apply(etld).notna()&(df['domain'].apply(etld)!=df['website'].apply(etld)))
df['comb']=df['s3']|df['d3']
def pres(c): return df[c].notna() & (df[c].astype(str).str.strip()!='')
df['pdef']=pres('initial_cookies')
CFG=[('DNT','do_not_track'),('Block','block_3rd_party'),('uBlock','ublock'),('GPC','gpc_enabled')]
for _,c in CFG: df['p_'+c]=pres(c)
df['old_g']=df['CCPA_Category'].apply(lambda v:'Subject' if str(v).strip()=='Subject to CCPA' else 'Not-Subject')
df['new_g']=df['nw'].apply(lambda w: newlab(w))
CATS=['Targeting','Performance','Functional','Strictly Necessary','Unknown']

def redT(m,cfg):
    d=int((m&df['pdef']).sum()); c=int((m&df['p_'+cfg]).sum()); return round(100*(1-c/d)) if d else 0
def red3(m,cfg):
    sub=df[m&df['comb']]
    dk=set(map(tuple,sub[sub['pdef']][['website','cookie_name']].values))
    gk=set(map(tuple,sub[sub['p_'+cfg]][['website','cookie_name']].values))
    return round(100*(1-len(dk&gk)/len(dk))) if dk else 0

def block(gcol,g,data):
    gm=data[gcol].eq(g)
    sites=data[gm]['website'].nunique(); tot=int((gm&data['pdef']).sum())
    print(f"  {g}: {sites} sites, {tot} cookies")
    def row(m,lab):
        n=int((m&data['pdef']).sum())
        if n==0: print(f"    {lab:20s} N=0"); return
        sc=100*(m&data['pdef']&data['s3']).sum()/n; dm=100*(m&data['pdef']&data['d3']).sum()/n
        cells=' '.join(f"{cn}:{redT(m,c)}({red3(m,c)})" for cn,c in CFG)
        print(f"    {lab:20s} N={n:5d} Scr={sc:4.1f} Dom={dm:4.1f} | {cells}")

    for cat in CATS: row(gm&df['ct'].eq(cat),cat)
    row(gm,'SUBTOTAL')

print("=== OLD (verify vs published: Subj 509/9749 Tgt N3150 Scr56.1 Dom4.2 GPC51(41); subtotal Scr42.7 GPC45(37); uBlock 67(82)) ===")
block('old_g','Subject',df); block('old_g','Not-Subject',df)

tm=df['website'].notna(); print(f"  TOTAL: {df['website'].nunique()} sites, {int(df['pdef'].sum())} cookies | Scr {100*(df['pdef']&df['s3']).sum()/df['pdef'].sum():.1f} | "+' '.join(f"{cn}:{redT(tm,c)}({red3(tm,c)})" for cn,c in CFG))

print("\n=== NEW (4 sites deleted; group by new labels) ===")
dN=df[~df['nw'].isin(EXC)].copy()

excmask=df['nw'].isin(EXC)
def blockN(g):
    gm=df['new_g'].eq(g)&(~excmask)
    sites=df[gm]['website'].nunique(); tot=int((gm&df['pdef']).sum())
    print(f"  {g}: {sites} sites, {tot} cookies")
    for cat in CATS:
        m=gm&df['ct'].eq(cat); n=int((m&df['pdef']).sum())
        if n==0: print(f"    {cat:20s} N=0"); continue
        sc=100*(m&df['pdef']&df['s3']).sum()/n; dm=100*(m&df['pdef']&df['d3']).sum()/n
        cells=' '.join(f"{cn}:{redT(m,c)}({red3(m,c)})" for cn,c in CFG)
        print(f"    {cat:20s} N={n:5d} Scr={sc:4.1f} Dom={dm:4.1f} | {cells}")
    n=int((gm&df['pdef']).sum()); sc=100*(gm&df['pdef']&df['s3']).sum()/n; dm=100*(gm&df['pdef']&df['d3']).sum()/n
    print(f"    {'SUBTOTAL':20s} N={n:5d} Scr={sc:4.1f} Dom={dm:4.1f} | "+' '.join(f"{cn}:{redT(gm,c)}({red3(gm,c)})" for cn,c in CFG))
blockN('Subject'); blockN('Not-Subject')
tmN=(~excmask)
print(f"  TOTAL: {df[tmN]['website'].nunique()} sites, {int((tmN&df['pdef']).sum())} cookies | Scr {100*(tmN&df['pdef']&df['s3']).sum()/(tmN&df['pdef']).sum():.1f} | "+' '.join(f"{cn}:{redT(tmN,c)}({red3(tmN,c)})" for cn,c in CFG))
