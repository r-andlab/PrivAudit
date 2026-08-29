# Usage: python build_ccpa_frame.py  |  Select the systematic 1,000-site CCPA-relevant Tranco expansion frame.
import csv, re, json, os, random, urllib.request, ssl
from concurrent.futures import ThreadPoolExecutor
random.seed(42)
HERE = os.path.join(os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "tranco_audit")
CACHE = f"{HERE}/probe_cache.jsonl"
KEEP_TLD = ('.com', '.org', '.net', '.us', '.io', '.co')
DROP_CCTLD = re.compile(r'\.(ru|jp|cn|de|it|br|fr|nl|in|ir|es|pl|tr|kr|vn|id|mx|ua|cz|se|no|fi|dk|ch|at|be|gr|pt|ro|hu|sk|il|sa|ae|th|ph|my|sg|hk|tw|au|nz|ca|uk|eu)$|\.(co|com)\.\w+$')

BANDS = [('top-1k', 1, 1000, 250, 900), ('1k-10k', 1001, 10000, 250, 900),
         ('10k-100k', 10001, 100000, 250, 900), ('100k-1M', 100001, 1000000, 250, 1600)]
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
EN_STOP = set('the and to of a in is for you your we our that with on this are it as be or from at by an will can more your all not have has'.split())
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def norm(d): d = re.sub(r'^https?://', '', str(d).strip().lower()); return re.sub(r'^www\.', '', d).split('/')[0]

def english(html):
    m = re.search(r'<html[^>]*\blang=["\']?([a-zA-Z-]+)', html)
    if m:
        return True if m.group(1).lower().startswith('en') else False
    txt = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S | re.I)
    words = re.findall(r"[a-z']{2,}", re.sub(r'<[^>]+>', ' ', txt).lower())
    if len(words) < 40: return None
    return (sum(1 for w in words if w in EN_STOP) / len(words)) > 0.10

def probe(domain):
    for scheme in ('https://', 'http://'):
        try:
            req = urllib.request.Request(scheme + domain, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=9, context=ctx) as r:
                ct = r.headers.get('Content-Type', '')
                if r.status != 200 or 'html' not in ct.lower():
                    return {'domain': domain, 'ok': False, 'reason': f'status/ct:{r.status}'}
                html = r.read(150000).decode('utf-8', 'ignore')
                en = english(html)
                return {'domain': domain, 'ok': en is True, 'lang': ('en' if en else ('non-en' if en is False else 'unk')),
                        'final': r.geturl()}
        except Exception as e:
            last = str(e).split('\n')[0][:60]
    return {'domain': domain, 'ok': False, 'reason': f'err:{last}'}

main = set()
mp = os.path.join(os.path.dirname(HERE), "subjectivity_reverify_input.csv")
if os.path.exists(mp):
    for r in csv.DictReader(open(mp)): main.add(norm(r['website']))
rows = list(csv.reader(open(f"{HERE}/top-1m.csv")))
if rows and not rows[0][0].isdigit(): rows = rows[1:]
data = [(int(r[0]), r[1].strip().lower()) for r in rows if len(r) >= 2 and r[0].isdigit()]
def tld_ok(d):
    return d.endswith(KEEP_TLD) and not DROP_CCTLD.search(d) and d.count('.') <= 1 and d not in main

cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try: j = json.loads(l); cache[j['domain']] = j
        except: pass
print(f"loaded {len(cache)} cached probes | main-corpus excludes: {len(main)}")

frame = []
cf = open(CACHE, 'a')
for name, lo, hi, quota, cap in BANDS:
    cand = [d for rank, d in data if lo <= rank <= hi and tld_ok(d)]
    random.shuffle(cand)
    cand = cand[:cap]
    todo = [d for d in cand if d not in cache]
    print(f"[{name}] {len(cand)} candidates, probing {len(todo)} new (quota {quota})...")
    with ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(probe, todo):
            cache[res['domain']] = res; cf.write(json.dumps(res) + '\n'); cf.flush()
    picked = [d for d in cand if cache.get(d, {}).get('ok')][:quota]
    frame += [(d, name) for d in picked]
    print(f"[{name}] English+active: {sum(1 for d in cand if cache.get(d,{}).get('ok'))} | picked {len(picked)}")
cf.close()

frame = frame[:1000]
with open(f"{HERE}/tranco_ccpa_frame_1000.txt", 'w') as f: f.write('\n'.join(d for d, _ in frame) + '\n')
with open(f"{HERE}/tranco_ccpa_frame_1000.csv", 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['domain', 'band']); w.writerows(frame)
print(f"\nFRAME: {len(frame)} sites | overlap w/ main corpus: {len(set(d for d,_ in frame) & main)}")
print("sample:", [d for d, _ in frame[:20]])
print(f"wrote tranco_ccpa_frame_1000.txt/.csv")
