const puppeteer = require('puppeteer');
const fs = require('fs');
const csvParser = require('csv-parser');

async function testGPC() {
  console.log('Testing GPC on 5 websites\n');

  // Read websites
  const websites = [];
  await new Promise((resolve) => {
    fs.createReadStream('input_csv/test_gpc.csv')
      .pipe(csvParser())
      .on('data', (row) => { if (row['Accessible Domain']) websites.push(row['Accessible Domain']); })
      .on('end', resolve);
  });

  console.log(`Loaded ${websites.length} websites\n`);

  const results = [];

  for (const website of websites) {
    console.log(`Processing: ${website}`);

    // Clean lock before each launch
    try { fs.unlinkSync('./chrome-user-data/SingletonLock'); } catch {}
    try { fs.unlinkSync('./chrome-user-data/Profile 5/SingletonLock'); } catch {}

    try {
      const browser = await puppeteer.launch({
        headless: true,
        executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        args: [
          '--user-data-dir=./chrome-user-data/',
          '--profile-directory=Profile 5'
        ]
      });

      const page = await browser.newPage();

      // Enable GPC
      console.log('   GPC enabled (Sec-GPC: 1)');
      await page.setExtraHTTPHeaders({ 'Sec-GPC': '1' });
      await page.evaluateOnNewDocument(() => {
        Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', {
          get: () => true,
          configurable: true
        });
      });

      await page.goto(`https://${website}`, { waitUntil: 'networkidle2', timeout: 30000 });
      await new Promise(r => setTimeout(r, 2000));

      const cookies = await page.cookies();
      console.log(`   Collected ${cookies.length} cookies\n`);

      cookies.forEach(c => {
        results.push({
          website,
          cookie_name: c.name,
          category: '',
          description: '',
          domain: c.domain,
          expires: c.expires,
          secure: c.secure,
          httpOnly: c.httpOnly,
          path: c.path,
          gpc_enabled: c.value
        });
      });

      await browser.close();
    } catch (err) {
      console.log(`   Error: ${err.message}\n`);
    }
  }

  // Save results
  const csv = [
    'website,cookie_name,category,description,domain,expires,secure,httpOnly,path,gpc_enabled',
    ...results.map(r => `${r.website},${r.cookie_name},${r.category},${r.description},${r.domain},${r.expires},${r.secure},${r.httpOnly},${r.path},${r.gpc_enabled}`)
  ].join('\n');

  fs.writeFileSync('result/test_gpc_output.csv', csv);

  console.log('\nTest complete!');
  console.log(`Total cookies collected: ${results.length}`);
  console.log(`Results saved to: result/test_gpc_output.csv\n`);

  console.log('Sample results:');
  results.slice(0, 5).forEach(r => console.log(`  - ${r.website} | ${r.cookie_name}`));
}

testGPC().catch(err => console.error('Error:', err.message));
