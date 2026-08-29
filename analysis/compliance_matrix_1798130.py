# Usage: python compliance_matrix_1798130.py  |  Section 1798.130(a)(5)(B) disclosure-vs-behavior compliance matrix.
import json, csv, re, collections, os
BASE = os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def norm(d):
    d = re.sub(r'^https?://', '', str(d).strip().lower()); d = re.sub(r'^www\.', '', d).split('/')[0]; return d

subj_label = {norm(r['website']): r['final_status'] for r in csv.DictReader(open(f"{BASE}/data/results/final_labels.csv")) if r['final_status'] in ('Subject', 'Not-Subject')}

pol = {}
for dom, rec in json.load(open(f"{BASE}/data/ccpa_policy_audit_data_source_mapped.json")).items():
    ad = rec.get('audit_data', {}); bc = ad.get('behavioral_claims', {})
    dm = ad.get('rubric_assessment', {}).get('disclosure_map', {})
    pol[norm(dom)] = {'sells': bc.get('sells_data'), 'shares': bc.get('shares_with_third_parties'),
                      'data_shared': dm.get('data_shared'), 'data_collected': dm.get('data_collected')}

sets3pt = collections.defaultdict(bool); has_cookie = set()
for r in csv.DictReader(open(f"{BASE}/data/final_default_state_comprehensive_reclassified.csv")):
    w = norm(r.get('website') or r.get('domain') or '')
    if not w: continue
    has_cookie.add(w)
    if r.get('category') == 'Targeting' and str(r.get('script_is_third_party')).strip().lower() == 'yes':
        sets3pt[w] = True

subject = [w for w in pol if subj_label.get(w) == 'Subject']
both = [w for w in subject if w in has_cookie]
setters = [w for w in both if sets3pt[w]]
silent_sell   = lambda w: pol[w]['sells'] == 'unspecified'
silent_share_claim = lambda w: pol[w]['shares'] == 'unspecified'
silent_share  = lambda w: pol[w]['shares'] == 'unspecified' and pol[w]['data_shared'] is not True

n = len(setters)
neither_cons = [w for w in setters if silent_sell(w) and silent_share(w)]
neither_claim = [w for w in setters if silent_sell(w) and silent_share_claim(w)]
print(f"subject w/ policy: {len(subject)} | + cookie data: {len(both)} | set >=1 3p Targeting: {n}")
print(f"silent on selling: {sum(silent_sell(w) for w in setters)} | silent on sharing (conservative): {sum(silent_share(w) for w in setters)}")
print(f"DISCLOSE NEITHER sale/share (conservative cross-field): {len(neither_cons)} ({100*len(neither_cons)/n:.1f}%)  [§1798.130(a)(5)(C)(i)]")
print(f"DISCLOSE NEITHER sale/share (claim-only, stricter):     {len(neither_claim)} ({100*len(neither_claim)/n:.1f}%)")
no_collect = [w for w in setters if pol[w]['data_collected'] is not True]
print(f"do NOT disclose data COLLECTION: {len(no_collect)} ({100*len(no_collect)/n:.1f}%)  [§1798.130(a)(5)(B)]")

os.makedirs(f"{BASE}/data/results", exist_ok=True)
with open(f"{BASE}/data/results/compliance_1798130_by_site.csv", 'w', newline='') as f:
    w_ = csv.writer(f); w_.writerow(['website', 'sets_3p_targeting', 'sells_claim', 'shares_claim', 'data_shared_disclosed',
                                     'silent_on_selling', 'silent_on_sharing', 'discloses_neither_conservative'])
    for w in sorted(both):
        w_.writerow([w, sets3pt[w], pol[w]['sells'], pol[w]['shares'], pol[w]['data_shared'],
                     silent_sell(w), silent_share(w), (sets3pt[w] and silent_sell(w) and silent_share(w))])
print("wrote data/results/compliance_1798130_by_site.csv")
