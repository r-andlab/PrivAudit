// Load configuration
const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");
const log = require("loglevel");

log.setLevel("info");

const config = JSON.parse(fs.readFileSync(path.join(__dirname, "config_gpc_only.json"), "utf8"));
const userDataDir = config.chrome.user_data_dir;
const chromeExecutablePath = config.chrome.executable_path;
const profile = config.profiles[0];

const failedWebsitesPath = path.join(__dirname, "../failed_websites.txt");
const failedWebsites = fs.readFileSync(failedWebsitesPath, "utf8")
  .split("\n")
  .filter(line => line.trim().length > 0);

log.info(`Found ${failedWebsites.length} failed websites to retry`);

const extractCookiesWithRetry = async (url, maxRetries = 3) => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    log.info(`Attempting ${url} (Try ${attempt}/${maxRetries})`);

    const profilePath = path.join(userDataDir, profile.directory);
    const singletonLockPath = path.join(profilePath, "SingletonLock");
    if (fs.existsSync(singletonLockPath)) {
      fs.unlinkSync(singletonLockPath);
    }

    let browser = null;
    try {
      browser = await puppeteer.launch({
        headless: true,
        executablePath: chromeExecutablePath,
        ignoreDefaultArgs: ["--disable-extensions"],
        args: [
          `--user-data-dir=${userDataDir}`,
          `--profile-directory=${profile.directory}`,
          "--no-default-browser-check",
          "--enable-extensions",
          "--disable-web-security",
          "--disable-features=IsolateOrigins,site-per-process",
        ],
      });

      const page = await browser.newPage();

      log.info("Enabling GPC signal (Sec-GPC: 1 header)");
      await page.setExtraHTTPHeaders({
        'Sec-GPC': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      });

      await page.evaluateOnNewDocument(() => {
        Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', {
          get: () => true,
          configurable: true
        });
      });

      await page.goto(`https://${url}`, {
        waitUntil: "networkidle2",
        timeout: 120000
      });

      await new Promise((resolve) => setTimeout(resolve, 3000));

      const cookies = await page.cookies();
      await page.close();
      await browser.close();

      log.info(`[OK] Successfully collected ${cookies.length} cookies from ${url}`);
      return { success: true, cookies, url };

    } catch (error) {
      if (browser) {
        try { await browser.close(); } catch (e) {}
      }

      log.warn(`Attempt ${attempt} failed for ${url}: ${error.message}`);

      if (attempt < maxRetries) {
        const waitTime = attempt * 2000;
        log.info(`Waiting ${waitTime}ms before retry...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
  }

  log.error(`[FAIL] All ${maxRetries} attempts failed for ${url}`);
  return { success: false, url };
};

const determineOutputFile = (website) => {

  const bannerPresentFile = path.resolve(__dirname, "../input_csv/cookies_banner_present.csv");
  const bannerNotPresentFile = path.resolve(__dirname, "../input_csv/cookies_banner_not_present.csv");

  const bannerPresentContent = fs.readFileSync(bannerPresentFile, "utf8");

  if (bannerPresentContent.includes(website)) {
    return config.paths.output_files.banner_present;
  } else {
    return config.paths.output_files.banner_not_present;
  }
};

const saveCookiesToCSV = (website, cookies, outputFile) => {
  const fullPath = path.join(__dirname, "..", outputFile);

  let existingContent = "";
  if (fs.existsSync(fullPath)) {
    existingContent = fs.readFileSync(fullPath, "utf8");
  }

  const rows = [];
  cookies.forEach((cookie) => {
    const currentTime = Math.floor(Date.now() / 1000);
    const remainingExpiryTime = cookie.expires ? Math.max(cookie.expires - currentTime, 0) : "Session";

    const cookieIdentifier = `${website},${cookie.name}`;
    if (existingContent.includes(cookieIdentifier)) {
      log.info(`Cookie ${cookie.name} for ${website} already exists, skipping`);
      return;
    }

    const row = [
      website,
      cookie.name,
      "",
      "",
      cookie.domain,
      cookie.expires || "",
      remainingExpiryTime,
      cookie.secure,
      cookie.httpOnly,
      cookie.path,
      cookie.priority || "",
      cookie.sameSite || "",
      cookie.session || false,
      new Date().toISOString(),
      cookie.value
    ].join(",");

    rows.push(row);
  });

  if (rows.length > 0) {
    fs.appendFileSync(fullPath, rows.join("\n") + "\n");
    log.info(`Appended ${rows.length} new cookies to ${outputFile}`);
  }
};

(async () => {
  const results = {
    successful: [],
    failed: []
  };

  log.info(`Starting retry process for ${failedWebsites.length} websites...`);
  log.info(`Enhanced settings: 120s timeout, 3 retry attempts, exponential backoff\n`);

  for (let i = 0; i < failedWebsites.length; i++) {
    const website = failedWebsites[i];
    log.info(`[${i + 1}/${failedWebsites.length}] Processing: ${website}`);

    const result = await extractCookiesWithRetry(website);

    if (result.success) {
      results.successful.push(website);

      const outputFile = determineOutputFile(website);
      saveCookiesToCSV(website, result.cookies, outputFile);
    } else {
      results.failed.push(website);
    }

    if ((i + 1) % 10 === 0) {
      log.info(`\n--- Progress: ${i + 1}/${failedWebsites.length} ---`);
      log.info(`Successful: ${results.successful.length}`);
      log.info(`Failed: ${results.failed.length}`);
      log.info(`Success rate: ${((results.successful.length / (i + 1)) * 100).toFixed(1)}%\n`);
    }
  }

  log.info("\n========== RETRY COMPLETE ==========");
  log.info(`Total processed: ${failedWebsites.length}`);
  log.info(`Successful recoveries: ${results.successful.length} (${((results.successful.length / failedWebsites.length) * 100).toFixed(1)}%)`);
  log.info(`Still failed: ${results.failed.length}`);

  if (results.failed.length > 0) {
    const stillFailedPath = path.join(__dirname, "../still_failed_websites.txt");
    fs.writeFileSync(stillFailedPath, results.failed.join("\n"));
    log.info(`\nStill-failed websites saved to: still_failed_websites.txt`);
  }

  log.info("=====================================\n");
})();
