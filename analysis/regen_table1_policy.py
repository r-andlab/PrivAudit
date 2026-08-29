# Usage: python regen_table1_policy.py  |  Reproduce Table 1 (policy results overall) on the re-verified labels.
import json, csv, re
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
    c=w2c.get(str(w).strip().lower())
    if c is None: return 'Not-Subject'
    return 'Subject' if 'subjected' in str(c).lower() else 'Not-Subject'
def newcat(w):
    l=newlab(w); return l if l in ('Subject','Not-Subject') else None

DISC=[('data_collected','Data Collection'),('data_shared','Data Sharing'),('opt_out','Opt Out'),
      ('purpose_of_collection','Purpose'),('retention_period','Retention'),('right_to_access','Access'),('right_to_delete','Delete')]
CLAIM=[('deletes_cookies_on_rejection','DeletesCookieAfterReject'),('sets_cookies_after_rejecting_consent','SetsAfterReject'),
       ('sets_cookies_before_consent','SetsBeforeConsent'),('uses_tracking_only_after_consent','TrackOnlyAfterConsent'),
       ('sells_data','SellsData'),('shares_with_third_parties','Shares3p'),('honors_gpc','HonorsGPC'),('respects_dnt','HonorsDNT')]

def compute(catfn):
    st={};
    for g in ('Subject','Not-Subject'):
        st[g]={'n':0,'disc':{k:0 for k,_ in DISC},'ment':{'Cookies':0,'CCPA':0,'Online':0,'Offline':0},
               'claim':{k:{'t':0,'f':0,'u':0} for k,_ in CLAIM}}
    for w,rec in audit.items():
        g=catfn(w)
        if g not in ('Subject','Not-Subject'): continue
        st[g]['n']+=1
        ad=rec.get('audit_data',{}); dm=ad.get('rubric_assessment',{}).get('disclosure_map',{}); bc=ad.get('behavioral_claims',{})
        on=(ad.get('online_data_practices','') or ''); off=(ad.get('offline_data_practices','') or '')
        for k,_ in DISC:
            if dm.get(k,False) is True: st[g]['disc'][k]+=1
        onl=on.lower()
        if 'cookie' in onl: st[g]['ment']['Cookies']+=1
        if 'ccpa' in onl or 'california consumer privacy act' in onl: st[g]['ment']['CCPA']+=1
        if on and len(on.strip())>20: st[g]['ment']['Online']+=1
        if off and len(off.strip())>20: st[g]['ment']['Offline']+=1
        for k,_ in CLAIM:
            v=bc.get(k,'unspecified')
            if v is True: st[g]['claim'][k]['t']+=1
            elif v is False: st[g]['claim'][k]['f']+=1
            else:
                s=str(v).lower()
                if s=='true': st[g]['claim'][k]['t']+=1
                elif s=='false': st[g]['claim'][k]['f']+=1
                else: st[g]['claim'][k]['u']+=1
    return st

def show(tag,st):
    print(f"\n===== {tag}  (Subject n={st['Subject']['n']} / Not n={st['Not-Subject']['n']}) =====")
    def pc(g,x): n=st[g]['n']; return 100*x/n if n else 0
    print("  DISCLOSURES (True% Subj / Not):")
    for k,lab in DISC: print(f"    {lab:14s} {pc('Subject',st['Subject']['disc'][k]):5.1f} / {pc('Not-Subject',st['Not-Subject']['disc'][k]):5.1f}")
    print("  MENTIONS (True% Subj / Not):")
    for m in ('Cookies','CCPA','Online','Offline'): print(f"    {m:14s} {pc('Subject',st['Subject']['ment'][m]):5.1f} / {pc('Not-Subject',st['Not-Subject']['ment'][m]):5.1f}")
    print("  BEHAVIORAL (T/F/U% Subj || Not):")
    for k,lab in CLAIM:
        s=st['Subject']['claim'][k]; nn=st['Not-Subject']['claim'][k]
        print(f"    {lab:22s} {pc('Subject',s['t']):4.1f}/{pc('Subject',s['f']):4.1f}/{pc('Subject',s['u']):4.1f}  ||  {pc('Not-Subject',nn['t']):4.1f}/{pc('Not-Subject',nn['f']):4.1f}/{pc('Not-Subject',nn['u']):4.1f}")

show("OLD (verify vs table: Subj 520/Not 417; OptOut 76.9/59.7; Sells 32.5/35.6/31.9 || 24.7/42.0/33.3; GPC 28.1/../71.5||15.6/../83.9; CCPA ment 67.3/43.1)",compute(oldcat))
show("NEW (final labels)",compute(newcat))
