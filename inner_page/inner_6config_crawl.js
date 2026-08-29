// Usage: node inner_6config_crawl.js  |  Crawl inner pages under six privacy configurations, recording third-party cookie/tracker writes per page.
const puppeteer = require('puppeteer');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { URL } = require('url');

const { PuppeteerBlocker } = require('@ghostery/adblocker-puppeteer');
const fetch = require('cross-fetch');
let blocker = null;

let com = null;

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const SAMPLE = process.argv[2] || 'inner_sample.txt';
const CONFIG = (process.argv[3] || 'default').toLowerCase();
const OUTPUT = process.argv[4] || `inner6_${CONFIG}.csv`;
const MAX_INNER = parseInt(process.argv[5] || '5', 10);
const START = parseInt(process.argv[6] || '0', 10);
const END = parseInt(process.argv[7] || '100000', 10);
const PAGE_TIMEOUT = 30000, SETTLE_MS = 3500, MAX_NET_RETRY = 6, NET_POLL_MS = 5000;
const EXT_DIR = path.join(__dirname, 'extensions');
const VALID = ['default','block3p','dnt','gpc','ublock','consentomatic'];
if(!VALID.includes(CONFIG)){ console.error(`config must be one of ${VALID.join(', ')}`); process.exit(1); }

const TWO = new Set(['co.uk','com.au','co.jp','co.nz','com.br','co.in','co.za','com.mx','org.uk','gov.uk','ac.uk','com.sg','co.kr']);
function etld1(host){ if(!host) return ''; host=host.replace(/^\./,'').toLowerCase(); const p=host.split('.');
  if(p.length>=3 && TWO.has(p.slice(-2).join('.'))) return p.slice(-3).join('.'); return p.length>=2?p.slice(-2).join('.'):host; }
function hostOf(u){ try{ return new URL(u).hostname; }catch(e){ return ''; } }
function esc(v){ if(v==null) return ''; const s=String(v); return /[",\n]/.test(s)?`"${s.replace(/"/g,'""')}"`:s; }
function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

function seedFrom(str){ let h=1779033703^str.length; for(let i=0;i<str.length;i++){ h=Math.imul(h^str.charCodeAt(i),3432918353); h=h<<13|h>>>19; } return h>>>0; }
function mulberry32(a){ return function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
function seededShuffle(arr, seedStr){ const r=mulberry32(seedFrom(seedStr)); const a=arr.slice();
  for(let i=a.length-1;i>0;i--){ const j=Math.floor(r()*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; }

const HEADER = 'website,site_etld1,config,page_type,page_url,cookie_name,cookie_domain,set_by_script_domain,set_method,script_is_third_party,domain_is_third_party\n';
if(!fs.existsSync(OUTPUT)) fs.writeFileSync(OUTPUT, HEADER);
const VISITED = OUTPUT + '.visited';
let visited = new Set();
if(fs.existsSync(VISITED)) visited = new Set(fs.readFileSync(VISITED,'utf-8').split('\n').map(s=>s.trim()).filter(Boolean));
function logln(m){ const l=`[${new Date().toISOString()}][${CONFIG}] ${m}`; console.log(l); fs.appendFileSync(OUTPUT+'.log', l+'\n'); }

async function isOnline(){ for(const u of ['https://www.google.com/generate_204','https://www.cloudflare.com/cdn-cgi/trace','https://captive.apple.com/hotspot-detect.html']){
  try{ const c=new AbortController(); const t=setTimeout(()=>c.abort(),4000);
    const r=await fetch(u,{method:'GET',signal:c.signal,redirect:'manual',cache:'no-store'}); clearTimeout(t); if(r&&r.status>0) return true; }catch(e){} } return false; }
async function waitForOnline(){ if(await isOnline()) return 0; let w=0; logln('⏸ network DOWN — pausing');
  while(!(await isOnline())){ await sleep(NET_POLL_MS); w+=NET_POLL_MS/1000; } logln(`▶ network back after ~${w}s`); return w; }
function isNetworkOutage(e){ return /ERR_INTERNET_DISCONNECTED|ERR_ADDRESS_INVALID|ERR_ADDRESS_UNREACHABLE|ERR_NETWORK_CHANGED|ERR_PROXY_CONNECTION_FAILED|ERR_NAME_RESOLUTION_FAILED/i.test(e||''); }
function isTransient(e){ return /ERR_HTTP2_PROTOCOL_ERROR|ERR_ABORTED|ERR_CONNECTION_RESET|ERR_CONNECTION_CLOSED|ERR_CONNECTION_TIMED_OUT|ERR_TIMED_OUT|ERR_SOCKET_NOT_CONNECTED|Navigation timeout/i.test(e||''); }

async function instrument(page){
  await page.evaluateOnNewDocument(() => {
    window.__cw = [];
    try {
      const proto = Document.prototype.hasOwnProperty('cookie') ? Document.prototype
                  : (HTMLDocument && HTMLDocument.prototype.hasOwnProperty('cookie') ? HTMLDocument.prototype : Document.prototype);
      const desc = Object.getOwnPropertyDescriptor(proto, 'cookie');
      if (desc && desc.set && desc.get) {
        Object.defineProperty(document, 'cookie', { configurable:true,
          get(){ return desc.get.call(document); },
          set(v){ try{ const name=String(v).split('=')[0].trim(); const stack=(new Error()).stack||''; window.__cw.push({name,stack}); }catch(e){} return desc.set.call(document, v); }
        });
      }
    } catch(e){}
  });
}
function scriptFromStack(stack){ if(!stack) return ''; const m=stack.match(/https?:\/\/[^\s):]+/g); if(!m) return '';
  for(const u of m){ if(!u.includes('/__cw')) return u; } return m[0]||''; }

async function applyPageConfig(page){
  if(CONFIG==='dnt'){
    await page.setExtraHTTPHeaders({ 'DNT':'1' });
    await page.evaluateOnNewDocument(() => { try{ Object.defineProperty(Navigator.prototype,'doNotTrack',{ get:()=>'1', configurable:true }); }catch(e){} });
  }
  if(CONFIG==='gpc'){
    await page.setExtraHTTPHeaders({ 'Sec-GPC':'1' });
    await page.evaluateOnNewDocument(() => { Object.defineProperty(Navigator.prototype,'globalPrivacyControl',{ get:()=>true, configurable:true }); });
  }
}
function launchOpts(){
  const baseArgs = ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled','--no-default-browser-check'];
  const opts = { headless:'new', executablePath:CHROME, args:baseArgs };

  if(CONFIG==='block3p'){

    const udd = fs.mkdtempSync(path.join(os.tmpdir(), 'blk3p-'));
    fs.mkdirSync(path.join(udd,'Default'), {recursive:true});
    fs.writeFileSync(path.join(udd,'Default','Preferences'),
      JSON.stringify({ profile:{ cookie_controls_mode:1, default_content_setting_values:{ cookies:1 }, block_third_party_cookies:true } }));
    opts.userDataDir = udd;
    opts.args.push('--test-third-party-cookie-phaseout');
  }
  return opts;
}

async function visitPage(context, site, siteE, url, pageType, out){
  const page = await context.newPage();
  const setCookies = [];
  try {
    await instrument(page); await applyPageConfig(page);
    if(CONFIG==='consentomatic' && com){ await page.evaluateOnNewDocument(com.shim); await page.evaluateOnNewDocument(com.content); }

    if(CONFIG==='ublock' && blocker){

      await blocker.enableBlockingInPage(page);
    } else {
      await page.setRequestInterception(true);
      page.on('request', req => { try { const t=req.resourceType(); if(t==='media'||t==='font') req.abort(); else req.continue(); } catch(e){ try{ req.continue(); }catch(_){} } });
    }
    page.on('response', resp => { try{ const h=resp.headers(); const sc=h['set-cookie']; if(sc){ const d=hostOf(resp.url());
      const lines=Array.isArray(sc)?sc:String(sc).split('\n'); for(const line of lines){ const nm=line.split('=')[0].trim(); if(nm) setCookies.push({name:nm,domain:d}); } } }catch(e){} });
    await page.goto(url, { waitUntil:'networkidle2', timeout:PAGE_TIMEOUT });
    await sleep(SETTLE_MS);
    if(CONFIG==='consentomatic') await sleep(5000);
    const jsWrites = await page.evaluate(()=>window.__cw||[]);
    const jsByName={}; for(const w of jsWrites){ if(!jsByName[w.name]) jsByName[w.name]=w.stack; }
    const cookies = await page.cookies();

    const attE = process.env.FINAL_REL ? (etld1(hostOf(page.url())) || siteE) : siteE;
    let inner=[];
    if(pageType==='home'){
      inner = await page.evaluate(()=>{ const out=[]; const seen=new Set();
        document.querySelectorAll('a[href]').forEach(a=>{ let href=a.href||''; if(!href.startsWith('http')) return;
          try{ const u=new URL(href); if(u.hash) u.hash=''; const c=u.toString(); if(!seen.has(c)){ seen.add(c); out.push(c); } }catch(e){} }); return out; });
    }
    const rows=[];
    for(const c of cookies){
      let setter='', method='unknown';
      if(jsByName[c.name]!==undefined){ setter=hostOf(scriptFromStack(jsByName[c.name])); method='JavaScript'; }
      else { const s=setCookies.find(x=>x.name===c.name); if(s){ setter=s.domain; method='HTTP'; } }
      const setterE=etld1(setter), cookieE=etld1((c.domain||'').replace(/^\./,''));
      const scriptTP = setterE ? (setterE!==attE?'Yes':'No') : '';
      const domainTP = cookieE && cookieE!==attE ? 'Yes':'No';
      rows.push([esc(site),esc(attE),esc(CONFIG),esc(pageType),esc(url),esc(c.name),esc(c.domain),esc(setter),esc(method),esc(scriptTP),esc(domainTP)].join(','));
    }
    if(rows.length) fs.appendFileSync(out, rows.join('\n')+'\n');
    await page.close();
    return { ok:true, n:cookies.length, inner };
  } catch(e){ try{ await page.close(); }catch(_){} return { ok:false, err:(e.message||'').split('\n')[0], inner:[] }; }
}

async function loadHomeWithRetry(browser, site, siteE, out){
  for(let attempt=1; attempt<=MAX_NET_RETRY; attempt++){
    await waitForOnline();
    const ctx = await browser.createBrowserContext();
    const home = await visitPage(ctx, site, siteE, `https://${site}`, 'home', out);
    await ctx.close();
    if(home.ok) return home;
    const err=home.err||'';
    if(isNetworkOutage(err)){ await waitForOnline(); continue; }
    if(!(await isOnline())){ await waitForOnline(); continue; }
    if(isTransient(err) && attempt===1){ await sleep(2000); continue; }
    return { ...home, realFail:true };
  }
  return { ok:false, err:'max-net-retries', realFail:false };
}

async function processSite(browser, site, out){
  const siteE = etld1(site);
  const home = await loadHomeWithRetry(browser, site, siteE, out);
  if(!home.ok){ logln(`✗ ${site} home: ${home.err}`); return { markVisited: home.realFail===true }; }

  const eligible=[]; const seenPath=new Set();
  for(const link of home.inner){
    if(etld1(hostOf(link))!==siteE) continue;
    let p=''; try{ p=new URL(link).pathname; }catch(e){ continue; }
    if(p===''||p==='/') continue;
    if(/\.(pdf|jpg|jpeg|png|gif|zip|mp4|svg|css|js)$/i.test(p)) continue;
    if(/(logout|signout|sign-out)/i.test(p)) continue;
    if(seenPath.has(p)) continue; seenPath.add(p);
    eligible.push(link);
  }
  const picks = seededShuffle(eligible, site).slice(0, MAX_INNER);
  let innerOk=0;
  for(const link of picks){
    const ctx = await browser.createBrowserContext();
    let r = await visitPage(ctx, site, siteE, link, 'inner', out);
    if(!r.ok && (isNetworkOutage(r.err)||isTransient(r.err))){ await waitForOnline(); r=await visitPage(ctx, site, siteE, link, 'inner', out); }
    await ctx.close();
    if(r.ok) innerOk++;
  }
  logln(`✓ ${site}: home=${home.n} cookies, inner ok=${innerOk}/${picks.length} (of ${eligible.length} eligible)`);
  return { markVisited:true };
}

(async () => {
  const all = fs.readFileSync(SAMPLE,'utf-8').split('\n').map(s=>s.trim()).filter(Boolean);
  const slice = all.slice(START, END).filter(s=>!visited.has(s));
  logln(`config=${CONFIG} | ${slice.length} sites to crawl (of ${all.length})`);
  if(CONFIG==='ublock'){ logln('building EasyList+EasyPrivacy blocker (uBlock-compatible rules)...'); blocker = await PuppeteerBlocker.fromPrebuiltAdsAndTracking(fetch); logln('blocker ready'); }
  if(CONFIG==='consentomatic'){ com = require('./com_inject.js').build(path.join(EXT_DIR,'consentomatic')); logln(`CoM engine ready (${com.nRules} CMP rules, inject mode)`); }
  let browser = await puppeteer.launch(launchOpts());
  let done=0;
  for(const site of slice){
    try{
      const r = await processSite(browser, site, OUTPUT);
      if(r.markVisited){ visited.add(site); fs.appendFileSync(VISITED, site+'\n'); }
    }catch(e){ logln(`‼ ${site}: ${(e.message||'').split('\n')[0]}`); }

    if(++done % 40 === 0){ try{ await browser.close(); }catch(_){} browser = await puppeteer.launch(launchOpts()); logln(`↻ recycled browser after ${done} sites`); }
  }
  try{ await browser.close(); }catch(_){}
  logln(`DONE config=${CONFIG}: ${done} sites processed`);
})();
