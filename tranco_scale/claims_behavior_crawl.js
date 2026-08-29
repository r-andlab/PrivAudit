// Usage: node claims_behavior_crawl.js  |  Crawl sites recording cookie-setting behavior (optionally with a GPC signal) to pair against policy claims.
const puppeteer = require('puppeteer');
const fs = require('fs');
const { URL } = require('url');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const SAMPLE = process.argv[2] || 'tranco_sample_1000.txt';
const OUTPUT = process.argv[3] || 'claims_behavior.csv';
const START = parseInt(process.argv[4] || '0', 10);
const END = parseInt(process.argv[5] || '100000', 10);
const PAGE_TIMEOUT = 45000;
const SETTLE_MS = 3500;

const TWO = new Set(['co.uk','com.au','co.jp','co.nz','com.br','co.in','co.za','com.mx','org.uk','gov.uk','ac.uk','com.sg','co.kr']);
function etld1(host){
  if(!host) return '';
  host = host.replace(/^\./,'').toLowerCase();
  const p = host.split('.');
  if(p.length>=3 && TWO.has(p.slice(-2).join('.'))) return p.slice(-3).join('.');
  return p.length>=2 ? p.slice(-2).join('.') : host;
}
function hostOf(u){ try{ return new URL(u).hostname; }catch(e){ return ''; } }
function esc(v){ if(v===null||v===undefined) return ''; const s=String(v); return /[",\n]/.test(s)?`"${s.replace(/"/g,'""')}"`:s; }

const HEADER = 'website,site_etld1,config,cookie_name,cookie_domain,set_by_script_domain,set_method,script_is_third_party,domain_is_third_party\n';
if(!fs.existsSync(OUTPUT)) fs.writeFileSync(OUTPUT, HEADER);

const VISITED = OUTPUT + '.visited';
let visited = new Set();
if(fs.existsSync(VISITED)) visited = new Set(fs.readFileSync(VISITED,'utf-8').split('\n').map(s=>s.trim()).filter(Boolean));

function logln(m){ const l=`[${new Date().toISOString()}] ${m}`; console.log(l); fs.appendFileSync(OUTPUT+'.log', l+'\n'); }

async function instrument(page, gpc){
  await page.evaluateOnNewDocument((gpcOn) => {
    if (gpcOn) {
      try { Object.defineProperty(navigator, 'globalPrivacyControl', { get: () => true, configurable: true }); } catch(e){}
    }
    window.__cw = [];
    try {
      const proto = Document.prototype.hasOwnProperty('cookie') ? Document.prototype
                  : (HTMLDocument && HTMLDocument.prototype.hasOwnProperty('cookie') ? HTMLDocument.prototype : Document.prototype);
      const desc = Object.getOwnPropertyDescriptor(proto, 'cookie');
      if (desc && desc.set && desc.get) {
        Object.defineProperty(document, 'cookie', {
          configurable: true,
          get(){ return desc.get.call(document); },
          set(v){
            try {
              const name = String(v).split('=')[0].trim();
              const stack = (new Error()).stack || '';
              window.__cw.push({ name, stack });
            } catch(e){}
            return desc.set.call(document, v);
          }
        });
      }
    } catch(e){}
  }, gpc);
}
function scriptFromStack(stack){
  if(!stack) return '';
  const m = stack.match(/https?:\/\/[^\s):]+/g);
  if(!m) return '';
  for(const u of m){ if(!u.includes('/__cw')) return u; }
  return m[0]||'';
}

async function visitHome(context, site, siteE, url, config, gpc, out){
  const page = await context.newPage();
  const setCookies = [];
  try {
    await instrument(page, gpc);
    if (gpc) await page.setExtraHTTPHeaders({ 'Sec-GPC': '1' });
    page.on('response', resp => {
      try{
        const h = resp.headers();
        const sc = h['set-cookie'];
        if(sc){
          const d = hostOf(resp.url());
          const lines = Array.isArray(sc)? sc : String(sc).split('\n');
          for(const line of lines){ const nm=line.split('=')[0].trim(); if(nm) setCookies.push({name:nm, domain:d}); }
        }
      }catch(e){}
    });
    await page.goto(url, { waitUntil:'networkidle2', timeout:PAGE_TIMEOUT });
    await new Promise(r=>setTimeout(r, SETTLE_MS));

    const jsWrites = await page.evaluate(()=>window.__cw || []);
    const jsByName = {};
    for(const w of jsWrites){ if(!jsByName[w.name]) jsByName[w.name]=w.stack; }

    const cookies = await page.cookies();
    const rows=[];
    for(const c of cookies){
      let setter='', method='unknown';
      if(jsByName[c.name]!==undefined){ setter=hostOf(scriptFromStack(jsByName[c.name])); method='JavaScript'; }
      else { const s=setCookies.find(x=>x.name===c.name); if(s){ setter=s.domain; method='HTTP'; } }
      const setterE = etld1(setter);
      const cookieE = etld1((c.domain||'').replace(/^\./,''));
      const scriptTP = setterE ? (setterE!==siteE ? 'Yes':'No') : '';
      const domainTP = cookieE && cookieE!==siteE ? 'Yes':'No';
      rows.push([esc(site),esc(siteE),esc(config),esc(c.name),esc(c.domain),esc(setter),esc(method),esc(scriptTP),esc(domainTP)].join(','));
    }
    if(rows.length) fs.appendFileSync(out, rows.join('\n')+'\n');
    await page.close();
    return { ok:true, n:cookies.length };
  } catch(e){
    try{ await page.close(); }catch(_){}
    return { ok:false, err:e.message.split('\n')[0] };
  }
}

async function processSite(browser, site, out){
  const siteE = etld1(site);
  let ok=0, res={};
  for(const [config, gpc] of [['default',false],['gpc',true]]){
    const ctx = await browser.createBrowserContext();
    const r = await visitHome(ctx, site, siteE, `https://${site}`, config, gpc, out);
    await ctx.close();
    res[config]=r.ok?r.n:`err(${r.err})`;
    if(r.ok) ok++;
  }
  logln(`${ok===2?'✓':'△'} ${site}: default=${res.default} gpc=${res.gpc}`);
  return {ok:ok>0};
}

(async()=>{
  const all = fs.readFileSync(SAMPLE,'utf-8').split('\n').map(s=>s.trim()).filter(Boolean);
  const slice = all.slice(START, END).filter(s=>!visited.has(s));
  logln(`Claims-vs-behavior crawl: ${slice.length} sites to process (of ${all.length}); configs=default+gpc`);
  const browser = await puppeteer.launch({ headless:true, executablePath:CHROME,
    args:['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled'] });
  for(let i=0;i<slice.length;i++){
    const site=slice[i];
    logln(`[${i+1}/${slice.length}] ${site}`);
    try{ await processSite(browser, site, OUTPUT); }catch(e){ logln(`✗ ${site} fatal: ${e.message.split('\n')[0]}`); }
    fs.appendFileSync(VISITED, site+'\n');
  }
  await browser.close();
  logln('DONE');
})().catch(e=>{ logln('FATAL '+e.message); process.exit(1); });
