# Usage: python apollo_reclassify.py  |  Re-verify CCPA subjectivity from Apollo revenue + free entity/HQ sources (Wikidata/EDGAR/ProPublica/GLEIF) and compare to the original labels.
import csv, json, re, os, collections
BASE=os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APOLLO=os.path.expanduser("~/Downloads/apollo-accounts-export-2.csv")
THRESH=25_000_000
def norm(d):
    d=re.sub(r'^https?://','',str(d or '').strip().lower()); d=re.sub(r'^www\.','',d).split('/')[0]; return d
def has(t,*k): t=(t or '').lower(); return any(x in t for x in k)
US_ST=set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split())
def usc(c): return (c or '').strip().lower() in ("united states","united states of america","usa","us")
def parserev(v):
    s=str(v or '').strip().lower().replace('$','').replace(',','')
    if not s: return None
    m=1.0
    if s[-1]=='b': m,s=1e9,s[:-1]
    elif s[-1]=='m': m,s=1e6,s[:-1]
    elif s[-1]=='k': m,s=1e3,s[:-1]
    try: return float(s)*m
    except: return None

orig={}
for r in csv.DictReader(open(f"{BASE}/data/subjectivity_reverify_input.csv")):
    orig[norm(r['website'])]=(r['current_ccpa_label'] or '').strip()
def old_status(lbl):
    l=(lbl or '').lower()
    if l.startswith('subjected'): return 'Subject'
    return 'Not-Subject'

apollo={}
for r in csv.DictReader(open(APOLLO, encoding='utf-8-sig')):
    d=norm(r.get('Domain') or r.get('Website'))
    if d: apollo[d]={'rev':parserev(r.get('Annual Revenue')),'ind':(r.get('Industry') or '').lower()}

wd=json.load(open(f"{BASE}/data/results/wikidata_enrich_raw.json"))
edg={r['website']:r for r in csv.DictReader(open(f"{BASE}/data/results/edgar_enriched.csv"))} if os.path.exists(f"{BASE}/data/results/edgar_enriched.csv") else {}
def load(p):
    return {r['website']:r for r in csv.DictReader(open(p))} if os.path.exists(p) else {}
pp=load(f"{BASE}/data/results/propublica_enriched.csv")
gl=load(f"{BASE}/data/results/gleif_enriched.csv")

OV={}
ovp=f"{BASE}/data/results/manual_label_overrides.csv"
if os.path.exists(ovp):
    for r in csv.DictReader(open(ovp)): OV[norm(r['website'])]={'label':(r['verified_label'] or '').strip(),'group':(r.get('group') or '').strip()}

def apollo_gov(ind): return has(ind,'government administration','government relations','legislative office','judiciary','military','international affairs','political organization','public policy office')
def apollo_np(ind):  return has(ind,'non-profit','nonprofit','philanthropy','fund-raising','religious institutions','civic & social organization')
def apollo_edu(ind): return has(ind,'higher education','education management','primary/secondary education')
def wd_gov(wt):  return has(wt,'government agency','federal agency','executive department','ministry','public authority','state government','municipality','intergovernmental organization','space agency','armed forces')
def wd_np(wt):   return has(wt,'nonprofit organization','non-profit organization','charitable organization','voluntary association','ngo','501(c)')
def wd_edu(wt):  return has(wt,'university','college','higher education institution')

def wd_commercial(wt): return has(wt,'business','enterprise','public company','privately held company','private company','private not-for-profit','brand','publisher','newspaper','magazine','periodical','crowdfunding platform','online service','online newspaper','retail','manufacturer','airline','record label','law firm')
def is_gov(ind,wt,host,rev,public):
    if host.endswith(('.gov','.mil','.int')): return True
    if wd_gov(wt): return not (public or (rev and rev>=THRESH))
    return apollo_gov(ind) and not wd_commercial(wt) and not (rev and rev>=THRESH)
def is_np(ind,wt,d,rev,public):
    if wd_np(wt): return True

    if apollo_np(ind) and not wd_commercial(wt): return True

    if pp.get(d,{}).get('pp_is_nonprofit')=='yes' and not public and not wd_commercial(wt) and d.endswith(('.org','.edu')):
        return True
    return False
def is_edu(ind,wt,host): return host.endswith('.edu') or wd_edu(wt) or (apollo_edu(ind) and not wd_commercial(wt))

rows=[]; ct=collections.Counter(); chg=[]
alld=set(orig)|set(apollo)
for d in sorted(alld):
    a=apollo.get(d,{}); w=wd.get(d) or {}; e=edg.get(d,{})
    wt=' '.join(w.get('types',[])); ind=a.get('ind','')
    host=d

    rev=a.get('rev')
    if rev is None and e.get('edgar_revenue_usd'): rev=float(e['edgar_revenue_usd'])
    wrev=None
    if w.get('rev'):
        try: wrev=float(w['rev'][1])
        except: pass
    public = has(wt,'public company') or (e.get('match')=='matched')

    country_us=(e.get('edgar_state','') in US_ST) or usc(w.get('country','')) or usc(gl.get(d,{}).get('gleif_country',''))
    country_known=bool(e.get('edgar_state')) or bool(w.get('country')) or bool(gl.get(d,{}).get('gleif_country'))
    foreign=country_known and not country_us

    if is_gov(ind,wt,host,rev,public): new='Not-Subject'; grp='government'
    elif is_np(ind,wt,d,rev,public):   new='Not-Subject'; grp='non_profit'
    elif is_edu(ind,wt,host): new='Not-Subject'; grp='non_profit'
    else:
        if rev is not None:
            new=('Subject' if rev>=THRESH else 'Not-Subject'); grp=('subjected' if rev>=THRESH else 'revenue_not_suff')
        elif public or (wrev is not None and wrev>=THRESH):
            new='Subject'; grp='subjected'
        else:
            new='Unknown'; grp='unknown'
    if grp=='subjected' and foreign: grp='subjected, location'
    rsrc=('apollo' if a.get('rev') is not None else ('edgar' if e.get('edgar_revenue_usd') else ('wikidata' if (wrev and wrev>=THRESH) else '')))
    ov=OV.get(d)
    if ov:
        new=ov['label']; rsrc='manual_verified'
        if new=='Subject': grp='subjected, location' if foreign else 'subjected'
        elif new=='Unknown': grp='unknown'
        elif ov.get('group'): grp=ov['group']
        elif grp not in ('non_profit','government'): grp='revenue_not_suff'
    old=old_status(orig.get(d,'')) if d in orig else 'n/a'
    ct[(old,new)]+=1
    rows.append(dict(website=d,old_label=orig.get(d,''),old_status=old,new_status=new,new_group=grp,
                     revenue=('' if rev is None else int(rev)),rev_source=rsrc,foreign=foreign))
    if old!='n/a' and new!='Unknown' and old!=new: chg.append((d,old,new,grp,rows[-1]['revenue']))

out=f"{BASE}/data/results/subjectivity_apollo_reclassified.csv"
with open(out,'w',newline='') as f:
    w_=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w_.writeheader(); w_.writerows(rows)

n=len(rows); newct=collections.Counter(r['new_status'] for r in rows); grpct=collections.Counter(r['new_group'] for r in rows)
print(f"=== Re-verification: NEW labels (Apollo revenue + free entity/HQ), paper's method ({n} domains) ===")
print("new 6-value groups:");
for g,c in grpct.most_common(): print(f"  {c:5d}  {g}")
print("\nnew binary:")
for s in ('Subject','Not-Subject','Unknown'): print(f"  {newct[s]:5d}  {s}")
comp=newct['Subject']+newct['Not-Subject']
print(f"  confidently labeled: {comp}/{n} = {100*comp/n:.0f}%  (Unknown/unresolved: {newct['Unknown']})")
print("\n=== OLD vs NEW confusion (excluding new=Unknown) ===")
print(f"{'':16s}{'new Subject':>13s}{'new Not-Subj':>13s}")
for o in ('Subject','Not-Subject'):
    print(f"  old {o:11s}{ct[(o,'Subject')]:>13d}{ct[(o,'Not-Subject')]:>13d}")
changed=sum(1 for r in rows if r['old_status'] in ('Subject','Not-Subject') and r['new_status'] in ('Subject','Not-Subject') and r['old_status']!=r['new_status'])
print(f"\nLABELS CHANGED (confident old vs confident new): {changed}")
print(f"  old Subject -> new Not-Subject: {ct[('Subject','Not-Subject')]}")
print(f"  old Not-Subject -> new Subject: {ct[('Not-Subject','Subject')]}")
print("\nsample changes (domain | old -> new | group | revenue):")
for d,o,nw,g,rv in chg[:25]: print(f"  {d:26s} {o:11s} -> {nw:11s} | {g:20s} | {('$'+format(rv,',')) if rv else '—'}")

def coarse(lbl):
    l=(lbl or '').lower()
    if l.startswith('subjected'): return 'subjected'
    if 'non' in l and 'profit' in l: return 'non_profit'
    if 'gov' in l: return 'government'
    if 'revenue' in l or 'not_suff' in l: return 'revenue_not_suff'
    if 'unknown' in l or l=='': return 'unknown'
    return l
flip_up=collections.Counter(); flip_dn=collections.Counter()
for r in rows:
    if r['old_status']=='Not-Subject' and r['new_status']=='Subject': flip_up[coarse(r['old_label'])]+=1
    if r['old_status']=='Subject' and r['new_status']=='Not-Subject': flip_dn[r['new_group']]+=1
print("\n=== Not-Subject -> Subject flips, by ORIGINAL fine label (originally 'unknown') ===")
for g,c in flip_up.most_common(): print(f"  {c:4d}  was '{g}'  -> now Subject (>=$25M revenue confirmed)")
print("=== Subject -> Not-Subject flips, by NEW reason ===")
for g,c in flip_dn.most_common(): print(f"  {c:4d}  now '{g}'")

oldu=[r for r in rows if coarse(r['old_label'])=='unknown']
print(f"\nOriginal 'unknown' sites (paper folded these into Not-Subject): {len(oldu)}")
uc=collections.Counter(r['new_status'] for r in oldu)
print(f"   re-check says -> Subject: {uc['Subject']}  |  Not-Subject: {uc['Not-Subject']}  |  still Unknown: {uc['Unknown']}")
print(f"\nwrote {out}")
