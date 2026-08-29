# Usage: python regen_overall_after_exclusion.py  |  Recompute the overall (label-independent) cookie ecosystem numbers after the 4-site exclusion.
import re, csv, pandas as pd
import os
BASE=os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); DATA=f"{BASE}/data"
def norm(x): x=re.sub(r'^https?://','',str(x).strip().lower()); return re.sub(r'^www\.','',x).split('/')[0]
EXC={'conservativetribune.com','findsimilar.com','futurescopes.com','ww2aircraft.net'}
df0=pd.read_csv(f"{DATA}/final_default_state_comprehensive_reclassified.csv",dtype=str,low_memory=False)
df0['nw']=df0['website'].apply(norm)
def etld(d):
    if pd.isna(d) or str(d)=='' : return None
    p=str(d).lstrip('.').split('.'); return '.'.join(p[-2:]) if len(p)>=2 else str(d)
def catn(v):
    k=str(v).strip().lower()
    if k in ('targeting','advertisement','targeting cookies'): return 'Targeting'
    if 'performance' in k: return 'Performance'
    if 'functional' in k: return 'Functional'
    if k in ('strictly necessary','necessary','strictly necessary cookies'): return 'Necessary'
    return 'Unknown'
def pres(df,c): return df[c].notna() & (df[c].astype(str).str.strip()!='')

def report(df,tag):
    n=len(df); print(f"\n===== {tag}: {n:,} cookies, {df['nw'].nunique()} sites =====")
    ct=df['category'].apply(catn)
    tgt=int((ct=='Targeting').sum())
    print(f"  total cookies={n:,} | Targeting={tgt:,} ({100*tgt/n:.1f}% of all)")
    s3=df['script_is_third_party'].fillna('No').astype(str).str.strip().eq('Yes')
    we=df['website'].apply(etld); ce=df['domain'].apply(etld)
    d3=(ce.notna()&we.notna()&(ce!=we))
    union=s3|d3
    print(f"  first-party(neither)={int((~union).sum()):,} ({100*(~union).mean():.1f}%) | third-party(union)={int(union.sum()):,} ({100*union.mean():.1f}%)")
    print(f"  script-3p={int(s3.sum()):,} ({100*s3.mean():.1f}%) | domain-3p={int(d3.sum()):,} ({100*d3.mean():.1f}%)")
    print(f"  script-only(1p-domain)={int((s3&~d3).sum()):,} ({100*(s3&~d3).mean():.1f}%) | both={int((s3&d3).sum()):,} ({100*(s3&d3).mean():.1f}%)")
    w3=df[union]['nw'].nunique(); print(f"  websites w/ >=1 third-party cookie={w3} ({100*w3/df['nw'].nunique():.1f}%)")
    unk=int((ct=='Unknown').sum()); print(f"  categorized={n-unk:,} ({100*(n-unk)/n:.1f}%) | Unknown={unk:,} ({100*unk/n:.1f}%)")

    for lbl,cfg in [('DNT','do_not_track'),('Block3P','block_3rd_party'),('GPC','gpc_enabled'),('uBlock','ublock')]:
        pd_=pres(df,'initial_cookies'); pc=pres(df,cfg)
        red=100*(1-int((pd_&pc).sum())/int(pd_.sum()))

        tm=(ct=='Targeting'); rt=100*(1-int((pd_&pc&tm).sum())/int((pd_&tm).sum()))
        pm=(ct=='Performance'); rp=100*(1-int((pd_&pc&pm).sum())/int((pd_&pm).sum()))
        print(f"  {lbl:7s} overall total red={red:.1f}% | Targeting red={rt:.1f}% | Performance red={rp:.1f}%")

report(df0,"FULL (verify vs paper: 19,152; tgt 6,406; 1p 58.4/3p 41.6; script 40.5; 670=72.9%; cat 70.7%; GPC tgt 55.7)")
report(df0[~df0['nw'].isin(EXC)].copy(),"AFTER REMOVING 4 (NEW canonical)")
