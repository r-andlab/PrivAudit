// usr/bin/env node
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const WEBSITES_FILE = 'websites_to_collect_gpc.txt';
const OUTPUT_FILE = 'gpc_only_data/cookies_missing_gpc.csv';
const LOG_FILE = 'missing_gpc_collection.log';
const FAILED_FILE = 'missing_gpc_failed.txt';
const ZERO_COOKIES_FILE = 'gpc_only_data/websites_zero_cookies_gpc.txt';

const CHROME_USER_DATA = './chrome-user-data/';
const CHROME_EXECUTABLE = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PROFILE_DIR = 'Profile 5';

const CSV_HEADER = 'website,cookie_name,category,description,domain,expires,remaining_expiry_time,secure,httpOnly,path,priority,sameSite,session,timestamp,gpc_enabled\n';

const websites = fs.readFileSync(WEBSITES_FILE, 'utf-8')
  .split('\n')
  .map(line => line.trim())
  .filter(line => line.length > 0);

console.log(`Loaded ${websites.length} websites to collect`);

if (!fs.existsSync(OUTPUT_FILE)) {
  fs.writeFileSync(OUTPUT_FILE, CSV_HEADER);
}

const failedSites = [];
const zeroCookiesSites = [];
let successCount = 0;
let failCount = 0;
let zeroCookiesCount = 0;

function log(message) {
  const timestamp = new Date().toISOString();
  const logMsg = `[${timestamp}] ${message}\n`;
  console.log(message);
  fs.appendFileSync(LOG_FILE, logMsg);
}

function escapeCSV(value) {
  if (value === null || value === undefined) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

async function collectCookies(website) {
  let browser;

  const strategies = [
    { protocol: 'https', waitUntil: 'networkidle2', timeout: 30000 },
    { protocol: 'https', waitUntil: 'domcontentloaded', timeout: 45000 },
    { protocol: 'http', waitUntil: 'domcontentloaded', timeout: 30000 },
    { protocol: 'https', waitUntil: 'load', timeout: 60000 }
  ];

  for (let strategyIdx = 0; strategyIdx < strategies.length; strategyIdx++) {
    const strategy = strategies[strategyIdx];

    try {
      if (strategyIdx > 0) {
        log(`  Retry ${strategyIdx}: ${website} with ${strategy.protocol}://, waitUntil=${strategy.waitUntil}`);
      } else {
        log(`Starting: ${website}`);
      }

      browser = await puppeteer.launch({
        headless: true,
        executablePath: CHROME_EXECUTABLE,
        userDataDir: CHROME_USER_DATA,
        args: [
          `--profile-directory=${PROFILE_DIR}`,
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-blink-features=AutomationControlled',
          '--ignore-certificate-errors',
          '--disable-http2'
        ]
      });

      const page = await browser.newPage();

      await page.setExtraHTTPHeaders({ 'Sec-GPC': '1' });
      await page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, 'globalPrivacyControl', {
          get: () => true,
          configurable: true
        });
      });

      const url = website.startsWith('http') ? website : `${strategy.protocol}://${website}`;

      await page.goto(url, {
        waitUntil: strategy.waitUntil,
        timeout: strategy.timeout
      });

      await new Promise(resolve => setTimeout(resolve, 3000));

      const cookies = await page.cookies();

      if (cookies.length === 0) {
        log(`[OK] ${website}: 0 cookies (tracked)`);
        zeroCookiesSites.push(website);
        zeroCookiesCount++;
      } else {
        log(`[OK] ${website}: ${cookies.length} cookies`);
      }

      if (cookies.length > 0) {
        const rows = cookies.map(cookie => {
          const expiresDate = cookie.expires > 0 ? new Date(cookie.expires * 1000) : null;
          const expiresStr = expiresDate ? expiresDate.toISOString() : '';
          const remainingExpiry = cookie.expires > 0 ? Math.max(0, cookie.expires - (Date.now() / 1000)) : '';

          return [
            escapeCSV(website),
            escapeCSV(cookie.name),
            escapeCSV(''),
            escapeCSV(''),
            escapeCSV(cookie.domain),
            escapeCSV(expiresStr),
            escapeCSV(remainingExpiry),
            escapeCSV(cookie.secure ? 'Yes' : 'No'),
            escapeCSV(cookie.httpOnly ? 'Yes' : 'No'),
            escapeCSV(cookie.path),
            escapeCSV(cookie.priority || ''),
            escapeCSV(cookie.sameSite || ''),
            escapeCSV(cookie.session ? 'Yes' : 'No'),
            escapeCSV(new Date().toISOString()),
            escapeCSV(cookie.name)
          ].join(',');
        }).join('\n') + '\n';

        fs.appendFileSync(OUTPUT_FILE, rows);
      }

      await browser.close();
      successCount++;
      return true;

    } catch (error) {

      if (browser) await browser.close().catch(() => {});

      if (strategyIdx === strategies.length - 1) {
        log(`[FAIL] ${website}: ${error.message}`);
        failedSites.push(website);
        failCount++;
        return false;
      }

    }
  }

  return false;
}

async function main() {
  log('='.repeat(60));
  log('GPC Missing Websites Collection');
  log('='.repeat(60));
  log(`Total websites: ${websites.length}`);
  log('');

  for (let i = 0; i < websites.length; i++) {
    const website = websites[i];
    log(`[${i + 1}/${websites.length}] Processing: ${website}`);
    await collectCookies(website);

    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  if (failedSites.length > 0) {
    fs.writeFileSync(FAILED_FILE, failedSites.join('\n') + '\n');
  }

  if (zeroCookiesSites.length > 0) {
    fs.writeFileSync(ZERO_COOKIES_FILE, zeroCookiesSites.join('\n') + '\n');
  }

  log('');
  log('='.repeat(60));
  log('Collection Complete');
  log('='.repeat(60));
  log(`Success: ${successCount}`);
  log(`  With cookies: ${successCount - zeroCookiesCount}`);
  log(`  Zero cookies: ${zeroCookiesCount}`);
  log(`Failed: ${failCount}`);
  log(`Output: ${OUTPUT_FILE}`);
  if (failedSites.length > 0) {
    log(`Failed list: ${FAILED_FILE}`);
  }
  if (zeroCookiesSites.length > 0) {
    log(`Zero cookies list: ${ZERO_COOKIES_FILE}`);
  }
  log('='.repeat(60));
}

main().catch(error => {
  log(`Fatal error: ${error.message}`);
  process.exit(1);
});
