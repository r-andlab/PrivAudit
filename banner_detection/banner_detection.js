// Load Configuration
import puppeteer from "puppeteer";
import fs from "fs";
import { createObjectCsvWriter } from "csv-writer";

const config = JSON.parse(fs.readFileSync("banner_detection/config.json", "utf-8"));

const bannersCsvWriter = createObjectCsvWriter({
    path: "banner_detection/banners_present.csv",
    append: true,
    header: [{ id: "Website", title: "Website" }]
});

const noBannerCsvWriter = createObjectCsvWriter({
    path: "banner_detection/banners_not_present.csv",
    append: true,
    header: [{ id: "Website", title: "Website" }]
});

const manualCsvWriter = createObjectCsvWriter({
    path: "banner_detection/manual_inspection.csv",
    append: true,
    header: [{ id: "Website", title: "Website" }]
});

const rawWebsites = fs.readFileSync(config.websites_file, "utf-8")
    .split("\n")
    .map(w => w.trim())
    .filter(w => w);
const websites = rawWebsites.map(domain => `https://${domain.toLowerCase()}`);

async function checkWebsite(browser, site, attempt = 1) {
    const page = await browser.newPage();
    try {
        console.log(`\n[INFO] Checking: ${site} (Attempt ${attempt})`);
        await page.goto(site, { waitUntil: "networkidle2", timeout: 30000 });

        let bannerFound = false;
        let detectedCMP = "Unknown";

        await page.waitForFunction(
            () => document.querySelector("div[id*='consent'], div[class*='cmp'], div[id*='onetrust-banner-sdk']"),
            { timeout: 2000 }
        ).catch(() => {});

        for (let selector of config.banner_selectors) {
            const banners = await page.$$(selector);
            if (banners.length > 0) {
                console.log(`[DEBUG] Found ${banners.length} elements matching ${selector}`);

                for (let banner of banners) {
                    const isVisible = await page.evaluate(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        const text = el.innerText.toLowerCase();
                        return style.display !== "none" &&
                            style.visibility !== "hidden" &&
                            style.opacity !== "0" &&
                            rect.width > 100 && rect.height > 10 &&
                            (text.includes("cookie") || text.includes("privacy") || text.includes("consent"));
                    }, banner);

                    if (isVisible) {
                        console.log(`[INFO] Visible banner detected using: ${selector}`);
                        bannerFound = true;
                        break;
                    }
                }
            }
            if (bannerFound) break;
        }

        if (!bannerFound) {
            console.log(`[INFO] No banner detected on ${site}`);
            return { Website: site, NoBanner: true };
        }

        for (let cmp in config.cmp_identifiers) {
            for (let selector of config.cmp_identifiers[cmp]) {
                const cmpElements = await page.$$(selector);
                if (cmpElements.length > 0) {
                    console.log(`[DEBUG] Found ${cmpElements.length} elements matching ${selector}`);

                    for (let cmpElement of cmpElements) {
                        const isCmpVisible = await page.evaluate(el => {
                            const style = window.getComputedStyle(el);
                            return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
                        }, cmpElement);

                        if (isCmpVisible) {
                            detectedCMP = cmp;
                            console.log(`[INFO] CMP Detected: ${cmp}`);
                            break;
                        }
                    }
                }
                if (detectedCMP !== "Unknown") break;
            }
        }

        if (!bannerFound) {
            console.log(`[INFO] Checking if banner is inside an iframe...`);
            const frames = page.frames();
            for (const frame of frames) {
                const iframeBanners = await frame.$$("div[id*='consent'], div[class*='cmp'], div[id*='onetrust-banner-sdk']");
                if (iframeBanners.length > 0) {
                    for (let banner of iframeBanners) {
                        const isVisible = await frame.evaluate(el => {
                            const style = window.getComputedStyle(el);
                            return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
                        }, banner);

                        if (isVisible) {
                            console.log(`[INFO] Banner detected inside iframe using: ${banner}`);
                            bannerFound = true;
                            break;
                        }
                    }
                }
                if (bannerFound) break;
            }
        }

        if (bannerFound && detectedCMP === "Unknown") {
            console.log(`[INFO] Banner detected, but CMP is unknown. Moving to manual inspection.`);
            return { Website: site, ManualReview: true };
        }

        return { Website: site, Banner: bannerFound, CMP: detectedCMP, ManualReview: false };

    } catch (error) {
        console.log(`[ERROR] Error processing ${site}: ${error.message}`);
        return { Website: site, Banner: "Error", CMP: "Error", ManualReview: false };
    } finally {
        await page.close().catch(() => console.log(`[WARNING] Page close failed for ${site}.`));
    }
}

(async () => {
    let browser = null;

    try {
        browser = await puppeteer.launch({
            headless: true,
            executablePath: config.chrome_executable,
            ignoreDefaultArgs: ["--disable-extensions"],
            args: [
                `--user-data-dir=${config.chrome_profile.user_data_dir}`,
                `--profile-directory=${config.chrome_profile.profile_directory}`,
                "--no-default-browser-check",
                "--enable-extensions",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]
        });

        for (let site of websites) {
            let result = await checkWebsite(browser, site);

            if (result.NoBanner) {
                await noBannerCsvWriter.writeRecords([{ Website: result.Website }]);
            } else if (result.ManualReview) {
                await manualCsvWriter.writeRecords([{ Website: result.Website }]);
            } else {
                await bannersCsvWriter.writeRecords([{ Website: result.Website }]);
            }
        }

    } catch (globalError) {
        console.log(`[ERROR] Critical Error: ${globalError.message}`);
    } finally {
        if (browser) {
            await browser.close();
        }
        console.log("[INFO] All results successfully saved. Exiting.");
    }
})();
