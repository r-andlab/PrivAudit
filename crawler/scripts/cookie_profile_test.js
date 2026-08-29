// Load configuration from JSON
const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");
const csvParser = require("csv-parser");
const log = require("loglevel");

log.setLevel("info");

console.log("Current Directory:", __dirname);
const config = JSON.parse(fs.readFileSync(path.join(__dirname, "config_gpc_only.json"), "utf8"));

const inputFiles = config.paths.input_files;
const outputFiles = config.paths.output_files;
const userDataDir = config.chrome.user_data_dir;
const chromeExecutablePath = config.chrome.executable_path;
const allProfiles = config.profiles;

const existingFiles = inputFiles.map(file => path.resolve(__dirname, file))
                                .filter(filePath => fs.existsSync(filePath));

console.log("Resolved Input Files:", existingFiles);

if (existingFiles.length === 0) {
  log.error("No input files found! Ensure at least one file (cookies_banner_present.csv or banner_not_present.csv) is available.");
  process.exit(1);
}

const profilesForBannerPresent = allProfiles;
const profilesForBannerNotPresent = allProfiles.slice(0, 5);

const getCsvHeaders = (profiles) => {
  return ["website", "cookie_name", "category", "description", "domain", "expires","remaining_expiry_time", "secure", "httpOnly", "path","priority","sameSite", "session", "timestamp", ...profiles.map(p => p.csv_field)];
};

const readWebsites = async (filePath) => {
  return new Promise((resolve, reject) => {
    const websites = [];
    fs.createReadStream(filePath)
      .pipe(csvParser())
      .on("data", (row) => {
        if (row["Accessible Domain"]) {
          websites.push(row["Accessible Domain"]);
        }
      })
      .on("end", () => {
        log.info(`Loaded ${websites.length} websites from ${filePath}`);
        resolve(websites);
      })
      .on("error", (error) => reject(error));
  });
};

const extractCookies = async (browser, url, profile) => {
  try {
    log.info(`Opening page: https://${url}`);
    const page = await browser.newPage();

    if (profile.name === "Profile 5") {
      log.info("Enabling GPC signal (Sec-GPC: 1 header)");
      await page.setExtraHTTPHeaders({
        'Sec-GPC': '1'
      });

      await page.evaluateOnNewDocument(() => {
        Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', {
          get: () => true,
          configurable: true
        });
      });
    }

    await page.goto(`https://${url}`, { waitUntil: "networkidle2", timeout: 60000 });
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const cookies = await page.cookies();
    await page.close();
    log.info("cookies fetched")
    return cookies;
  } catch (error) {
    log.error(`Error occurred while processing ${url}:`, error);
    return null;
  }
};

const saveResultsToCSV = (results, profiles, outputFile) => {
  log.info(`Saving results to ${outputFile}...`);
  const csvHeaders = getCsvHeaders(profiles);
  const csvContent = [csvHeaders.join(",")];

  Object.values(results).forEach((row) => {
    csvContent.push(
      csvHeaders.map((header) => (row[header] !== undefined ? row[header] : ""))
      .join(",")
    );
  });

  const dir = path.dirname(outputFile);
  if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
  }

  const fileExists = fs.existsSync(outputFile);
  const fileStream = fs.createWriteStream(outputFile, { flags: "a" });

  if (!fileExists) {
      fileStream.write(csvHeaders.join(",") + "\n");
  }

  csvContent.slice(1).forEach(line => fileStream.write(line + "\n"));
  fileStream.end();
  log.info(`Cookies data saved to ${outputFile}`);
};

const handleCookiesForFile = async (filePath, profiles, outputFile) => {
  log.info(`Starting cookies extraction process for ${filePath}...`);
  const websites = await readWebsites(filePath);
  const results = {};

  for (const website of websites) {
    log.info(`Processing website: ${website}`);
    let skipWebsite = false;

    for (const profile of profiles) {
      if (skipWebsite) break;
      log.info(`Using profile: ${profile.name}`);

      try {

        const chromiumPath = profile.name === "Profile 1" ? profile.executable_path : chromeExecutablePath;

        log.info(`Launching browser for profile: ${profile.name}`);
        log.info(`Using executable: ${chromiumPath}`);
        log.info(`User Data Directory: ${path.join(userDataDir, profile.directory)}`);

        const profilePath = path.join(userDataDir, profile.directory);
const singletonLockPath = path.join(profilePath, "SingletonLock");

if (fs.existsSync(singletonLockPath)) {
  log.warn(`Deleting SingletonLock file for profile: ${profile.name}`);
  fs.unlinkSync(singletonLockPath);
}

log.info(`Launching browser for profile: ${profile.name}`);

const browser = await puppeteer.launch({
  headless: true,
  executablePath: chromiumPath,
  ignoreDefaultArgs: ["--disable-extensions"],
  args: [
    `--user-data-dir=${userDataDir}`,
    `--profile-directory=${profile.directory}`,
    "--no-default-browser-check",
    "--enable-extensions",
  ],
});

        log.info(`Browser launched for profile: ${profile.name}`);

        const cookies = await extractCookies(browser, website, profile);
        await browser.close();

        if (!cookies) {
          log.warn(`Skipping ${website} for all profiles due to an error.`);
          skipWebsite = true;
          break;
        }

        cookies.forEach((cookie) => {
          const cookieKey = `${website}_${cookie.name}`;
          const currentTime = Math.floor(Date.now() / 1000);
          const remainingExpiryTime = cookie.expires ? Math.max(cookie.expires - currentTime, 0) : "Session";

          if (!results[cookieKey]) {
            results[cookieKey] = {
              website,
              cookie_name: cookie.name,
              category: "",
              description: "",
              domain: cookie.domain,
              expires: cookie.expires,
              remaining_expiry_time: remainingExpiryTime,
              secure: cookie.secure,
              httpOnly: cookie.httpOnly,
              path: cookie.path,
              priority: cookie.priority,
              sameSite: cookie.sameSite || "",
              session: cookie.session || false,
              timestamp: new Date().toISOString(),
            };

            profiles.map(p => p.csv_field).forEach(header => {
              results[cookieKey][header] = "";
            });
          }

          results[cookieKey][profile.csv_field] = cookie.value;
        });
      } catch (error) {
        log.error(`Error occurred for profile ${profile.name} on ${website}:`, error);
        skipWebsite = true;
        break;
      }
    }
  }

  saveResultsToCSV(results, profiles, outputFile);
};

(async () => {
  for (const file of existingFiles) {
    if (file.includes("banner_present")) {
      await handleCookiesForFile(file, profilesForBannerPresent, outputFiles.banner_present);
    } else if (file.includes("banner_not_present")) {
      await handleCookiesForFile(file, profilesForBannerNotPresent, outputFiles.banner_not_present);
    }
  }
  log.info("All tasks completed.");
})();
