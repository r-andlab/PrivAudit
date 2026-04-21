const fs = require("fs");
const puppeteer = require("puppeteer");
const csv = require("csv-parser");
const { parse } = require("json2csv");

// Load config
const config = JSON.parse(fs.readFileSync("cookie_categorization/config.json"));

const { cookies_to_fetch, failed_cookies, my_cookie_db, process_file } = config.file_paths;
const { max_retries, rate_limit_wait, concurrent_requests } = config.fetch_settings;
const headlessMode = config.puppeteer.headless;

let failedCookies = new Set(fs.existsSync(failed_cookies) ? JSON.parse(fs.readFileSync(failed_cookies)) : []);
let cookieDatabase = {};
let processData = [];

// Load existing `mycookiebase.csv`
if (fs.existsSync(my_cookie_db)) {
    const lines = fs.readFileSync(my_cookie_db, "utf-8").split("\n");
    for (let line of lines) {
        const [cookie, category, description] = line.split(",");
        if (cookie) {
            cookieDatabase[cookie.trim().toLowerCase()] = { 
                category: category?.trim() || "", 
                description: description?.trim() || "" 
            };
        }
    }
}

// Load `processed_cookies_banner_present.csv`
if (fs.existsSync(process_file)) {
    fs.createReadStream(process_file)
        .pipe(csv())
        .on("data", (row) => processData.push(row))
        .on("end", async () => {
            await fetchAndUpdateCookies();
        });
} else {
    console.log(`No process file found: ${process_file}`);
    process.exit(1);
}

// Fetch cookies from Cookiepedia with Parallel Requests
async function fetchAndUpdateCookies() {
    if (!fs.existsSync(cookies_to_fetch)) {
        console.log("No cookies to fetch.");
        return;
    }

    const cookies = JSON.parse(fs.readFileSync(cookies_to_fetch));
    const browser = await puppeteer.launch({ headless: headlessMode });

    const queue = [...cookies];  // Clone array
    while (queue.length > 0) {
        let batch = queue.splice(0, concurrent_requests); // Take `concurrent_requests` cookies at a time
        console.log(`Fetching batch: ${batch.join(", ")}`);
        
        const results = await Promise.all(batch.map(cookie => processCookie(browser, cookie)));

        // **Handle Rate Limit: If rate limited, pause for 10 minutes before continuing**
        if (results.includes("rate_limited")) {
            console.log("Rate limit hit! Waiting 10 minutes before retrying...");
            await new Promise(resolve => setTimeout(resolve, 10 * 60 * 1000));
        }

        // **Wait 40-70 seconds before fetching next batch**
        await randomDelay(40, 70);
    }

    await browser.close();
    fs.writeFileSync(cookies_to_fetch, JSON.stringify([]));  // Clear fetch list
    console.log("Completed Cookiepedia fetch and updated all files.");
}

// Process each cookie
async function processCookie(browser, cookie) {
    const lowerCookie = cookie.toLowerCase(); // Normalize case
    if (failedCookies.has(lowerCookie)) {
        console.log(`Skipping ${cookie} (previously failed)`);
        return;
    }

    let page = await browser.newPage();
    let attempts = 0;

    while (attempts < max_retries) {
        try {
            await page.goto(`https://cookiepedia.co.uk/cookies/${cookie}`, { waitUntil: "domcontentloaded" });

            const pageContent = await page.content();
            if (pageContent.includes("Error 1015") || pageContent.includes("You are being rate limited")) {
                console.log("Rate limit detected! Waiting before retrying...");
                await page.close();
                return "rate_limited"; // Signal that a rate limit was hit
            }

            const category = await page.evaluate(() => document.querySelector("strong")?.innerText.trim() || "Unknown");
            const description = await page.evaluate(() => document.body.innerText.match(/This cookie name (.*?)\./)?.[1] || "");

            console.log(`Fetched ${cookie}: ${category} | ${description}`);

            // Check if data is invalid (Unknown category OR no description)
            if (category.toLowerCase() === "unknown" && !description) {
                console.log(`Marking ${cookie} as failed (Invalid Data)`);
                failedCookies.add(lowerCookie);
                saveFailedCookies();  // **Save failed cookies immediately**
                return;
            }

            // Update `my_cookie_db`
            cookieDatabase[lowerCookie] = { category, description };
            saveMyCookieDatabase();  // **Save immediately**

            // Update `processed_cookies_banner_present.csv`
            let rowIndex = processData.findIndex(row => row["cookie_name"].toLowerCase() === lowerCookie);

            if (rowIndex !== -1) {
                console.log(`Updating processed file entry for: ${cookie}`);
                processData[rowIndex]["category"] = category;
                processData[rowIndex]["description"] = description;

                saveProcessFile();  // Save immediately
                console.log(`Updated ${process_file} with ${cookie}: ${category} | ${description}`);
            } else {
                console.log(`WARNING: ${cookie} not found in processed file. (Possible case mismatch)`);
            }

            await page.close();
            return "success";

        } catch (error) {
            console.error(`Error fetching ${cookie}:`, error);
            attempts++;
            if (attempts >= max_retries) {
                failedCookies.add(lowerCookie);
                saveFailedCookies();  // **Save failed cookies immediately**
            }
        }
    }
    await page.close();
    return "failed";
}

// Function to generate random delay (40-70 seconds)
function randomDelay(min, max) {
    const delay = Math.floor(Math.random() * (max - min + 1) + min) * 1000;
    console.log(`Waiting ${delay / 1000} seconds before next request...`);
    return new Promise(resolve => setTimeout(resolve, delay));
}

// Save `my_cookie_db` immediately
function saveMyCookieDatabase() {
    const dbLines = Object.entries(cookieDatabase).map(([cookie, data]) => `${cookie},${data.category},${data.description}`);
    fs.writeFileSync(my_cookie_db, dbLines.join("\n"));
    console.log(`Updated ${my_cookie_db} immediately.`);
}

// Save `processed_cookies_banner_present.csv` immediately
function saveProcessFile() {
    console.log(`Writing updates to ${process_file}`);
    const csvData = parse(processData);
    fs.writeFileSync(process_file, csvData);
    console.log(`Updated ${process_file} successfully.`);
}

// Save failed cookies immediately
function saveFailedCookies() {
    fs.writeFileSync(failed_cookies, JSON.stringify(Array.from(failedCookies), null, 2));
    console.log(`Updated ${failed_cookies} with failed cookies.`);
}