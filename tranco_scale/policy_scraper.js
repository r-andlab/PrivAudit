// Usage: node policy_scraper.js  |  Locate each site's privacy-policy link and extract its readable text.
const puppeteer = require('puppeteer');
const fs = require('fs');
const { URL } = require('url');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const SAMPLE = process.argv[2] || 'tranco_sample_1000.txt';
const OUTPUT = process.argv[3] || 'policies.jsonl';
const START = parseInt(process.argv[4] || '0', 10);
const END = parseInt(process.argv[5] || '100000', 10);
const NAV_TIMEOUT = 40000;
const SETTLE_MS = 2500;
const MAX_TEXT = 200000;
const COMMON_PATHS = ['/privacy', '/privacy-policy', '/privacypolicy', '/privacy-notice',
  '/privacy-statement', '/legal/privacy', '/en/privacy', '/policies/privacy', '/about/privacy'];

const VISITED = OUTPUT + '.visited';
let visited = new Set();
if (fs.existsSync(VISITED)) visited = new Set(fs.readFileSync(VISITED, 'utf-8').split('\n').map(s => s.trim()).filter(Boolean));
function logln(m){ const l=`[${new Date().toISOString()}] ${m}`; console.log(l); fs.appendFileSync(OUTPUT+'.log', l+'\n'); }
function hostOf(u){ try{ return new URL(u).hostname; }catch(e){ return ''; } }

function scorePrivacy(text, href){
  const t=(text||'').trim().toLowerCase().replace(/\s+/g,' ');
  const h=(href||'').toLowerCase();
  if(/\bprivacy (policy|notice|statement)\b/.test(t)) return {s:100, by:'text:privacy-policy'};
  if(/\bprivacy\b/.test(t) && /\b(policy|notice|statement|rights|center)\b/.test(t)) return {s:92, by:'text:privacy-compound'};
  if(t==='privacy'||t==='privacy & cookies'||t==='privacy and cookies') return {s:84, by:'text:privacy'};
  if(/\bprivacy\b/.test(t)) return {s:74, by:'text:privacy-word'};
  if(/privacy-?(policy|notice|statement)/.test(h)) return {s:66, by:'href:privacy-policy'};
  if(/privacy/.test(h)) return {s:52, by:'href:privacy'};
  return {s:0, by:''};
}
function isCcpaOptOut(text, href){
  const t=(text||'').toLowerCase(), h=(href||'').toLowerCase();
  return /do not sell|do not share|your privacy choices|california privacy|limit the use of my|your california privacy/.test(t)
      || /do-?not-?sell|privacy-?choices|california-?privacy|ccpa|dns(mpi)?/.test(h);
}
function detectLang(text){
  const s=text.slice(0,5000).toLowerCase();
  const en=(s.match(/\b(the|and|to|of|you|we|your|our|information|data|privacy|personal|use|rights)\b/g)||[]).length;
  const w=(s.match(/[a-zÀ-ɏ]+/g)||[]).length||1;
  return en/w>0.05?'en-likely':'non-en-likely';
}

async function newPage(browser){
  const ctx = await browser.createBrowserContext();
  const page = await ctx.newPage();
  await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36');
  return {ctx, page};
}

async function extractText(page){
  return await page.evaluate(()=>{
    const kill=['script','style','noscript','svg','nav','header','footer','iframe','form','button','input','select'];
    kill.forEach(sel=>document.querySelectorAll(sel).forEach(n=>n.remove()));
    document.querySelectorAll('[id*="cookie" i],[class*="cookie" i],[class*="banner" i],[class*="consent" i],[aria-hidden="true"]')
      .forEach(n=>{ try{n.remove();}catch(e){} });
    const cands=['main','article','[role="main"]','#content','#main','.content','.main-content','.policy','.privacy-policy','.legal','body'];
    let best='', bestLen=0;
    for(const sel of cands){
      document.querySelectorAll(sel).forEach(el=>{
        const txt=(el.innerText||'').replace(/\n{3,}/g,'\n\n').trim();
        if(txt.length>bestLen){ best=txt; bestLen=txt.length; }
      });
    }
    return best;
  });
}

async function findLinks(page){
  return await page.evaluate(()=>{
    const out=[];
    document.querySelectorAll('a[href]').forEach(a=>{
      const href=a.href||''; if(!href.startsWith('http')) return;
      out.push({text:(a.innerText||a.textContent||'').trim().slice(0,120), href});
    });
    return out;
  });
}

async function grabPolicy(browser, url){
  const {ctx, page} = await newPage(browser);
  try{
    const resp = await page.goto(url, {waitUntil:'networkidle2', timeout:NAV_TIMEOUT});
    await new Promise(r=>setTimeout(r, SETTLE_MS));
    const ct = (resp && resp.headers()['content-type']) || '';
    if(/pdf/i.test(ct) || /\.pdf($|\?)/i.test(url)){
      await ctx.close();
      return {status:'pdf', url, text:'', lang:'', ccpa:''};
    }

    let ccpa='';
    try{ const ls=await findLinks(page); for(const l of ls){ if(isCcpaOptOut(l.text,l.href)){ ccpa=l.href; break; } } }catch(e){}
    let text = await extractText(page);
    if(text.length>MAX_TEXT) text=text.slice(0,MAX_TEXT);
    const finalUrl = page.url();
    await ctx.close();
    const low = text.slice(0,700).toLowerCase();
    const is404 = /(page|content|url).{0,20}(not found|cannot be found|couldn'?t be found)|404 error|\bnot found\b|no longer (exists|available)|does(n'?t| not) exist/.test(low);
    const hasPolicySignal = /(personal (information|data)|we collect|information we collect|privacy (policy|notice|statement)|your (data|information)|use of cookies|data protection|opt[- ]?out)/.test(text.toLowerCase());
    if(is404) return {status:'notfound', url:finalUrl, text:'', lang:'', ccpa};
    if(text.length < 400 || !hasPolicySignal) return {status:'thin', url:finalUrl, text, lang:detectLang(text), ccpa};
    return {status:'ok', url:finalUrl, text, lang:detectLang(text), ccpa};
  }catch(e){
    try{ await ctx.close(); }catch(_){}
    return {status:'error:'+e.message.split('\n')[0], url, text:'', lang:'', ccpa:''};
  }
}

async function processDomain(browser, domain, out){
  const rec = {domain, homepage_status:'', policy_url:'', matched_by:'', policy_status:'',
    ccpa_optout_url:'', text_len:0, lang:'', text:'', ts:new Date().toISOString()};

  const {ctx, page} = await newPage(browser);
  let links=[];
  try{
    const r = await page.goto(`https://${domain}`, {waitUntil:'networkidle2', timeout:NAV_TIMEOUT});
    await new Promise(res=>setTimeout(res, SETTLE_MS));
    rec.homepage_status = r ? String(r.status()) : 'noresp';
    links = await findLinks(page);
  }catch(e){
    rec.homepage_status = 'error:'+e.message.split('\n')[0];
  }
  await ctx.close();

  let best={s:0, by:'', href:''};
  for(const l of links){
    const sc=scorePrivacy(l.text, l.href);
    if(sc.s>best.s) best={s:sc.s, by:sc.by, href:l.href};
    if(!rec.ccpa_optout_url && isCcpaOptOut(l.text, l.href)) rec.ccpa_optout_url = l.href;
  }

  let got=null;
  if(best.s>0){
    got = await grabPolicy(browser, best.href);
    rec.matched_by = best.by;
  }
  if(!got || got.status!=='ok'){
    for(const p of COMMON_PATHS){
      const cand = `https://${domain}${p}`;
      const g = await grabPolicy(browser, cand);
      if(g.status==='ok'){ got=g; rec.matched_by='fallback:'+p; break; }
      if(!got) got=g;
    }
  }
  if(got){
    rec.policy_url = got.url; rec.policy_status = got.status;
    rec.text = got.text || ''; rec.text_len = rec.text.length; rec.lang = got.lang || '';
    if(!rec.ccpa_optout_url && got.ccpa) rec.ccpa_optout_url = got.ccpa;
  } else {
    rec.policy_status = 'no-link-found';
  }
  fs.appendFileSync(out, JSON.stringify(rec)+'\n');
  const tag = rec.policy_status==='ok' ? '✓' : (rec.policy_status==='pdf'?'▤':'△');
  logln(`${tag} ${domain}: hp=${rec.homepage_status} policy=${rec.policy_status} len=${rec.text_len} ${rec.matched_by} ${rec.ccpa_optout_url?'[CCPA-optout]':''}`);
  return rec.policy_status==='ok';
}

(async()=>{
  const all = fs.readFileSync(SAMPLE,'utf-8').split('\n').map(s=>s.trim()).filter(Boolean);
  const slice = all.slice(START, END).filter(s=>!visited.has(s));
  logln(`Policy scrape: ${slice.length} domains to process (of ${all.length})`);
  const browser = await puppeteer.launch({ headless:true, executablePath:CHROME,
    args:['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled'] });
  let ok=0;
  for(let i=0;i<slice.length;i++){
    const d=slice[i];
    logln(`[${i+1}/${slice.length}] ${d}`);
    try{ if(await processDomain(browser, d, OUTPUT)) ok++; }
    catch(e){ logln(`✗ ${d} fatal: ${e.message.split('\n')[0]}`); }
    fs.appendFileSync(VISITED, d+'\n');
  }
  await browser.close();
  logln(`DONE. policy_ok=${ok}/${slice.length}`);
})().catch(e=>{ logln('FATAL '+e.message); process.exit(1); });
