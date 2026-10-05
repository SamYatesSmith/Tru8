// Retry pages a plain fetch could not read: real Chromium for HTML, pdf text for PDFs.
// Input: a JSON list of URLs. Output: {url: text|null} (main text = document.body.innerText).
// Usage (from web/): node ../audit/echo_precision/refetch_browser.mjs URLS.json OUT.json
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire('C:/Users/projects/Tru8/web/package.json');
const { chromium } = require('playwright');

const [, , IN, OUT] = process.argv;
const urls = JSON.parse(fs.readFileSync(IN, 'utf8'));
const out = {};
const browser = await chromium.launch();
const ctx = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
  locale: 'en-GB',
});
let i = 0;
async function worker() {
  while (i < urls.length) {
    const url = urls[i++];
    const page = await ctx.newPage();
    try {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2500);
      const status = resp ? resp.status() : 0;
      const text = await page.evaluate(() => {
        const m = document.querySelector('article') || document.querySelector('main') || document.body;
        return m ? m.innerText : '';
      });
      out[url] = status < 400 && text && text.length >= 200 ? text : null;
    } catch (e) {
      out[url] = null;
    } finally {
      await page.close();
    }
  }
}
await Promise.all(Array.from({ length: 6 }, worker));
await browser.close();
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('urls', urls.length, 'ok', Object.values(out).filter(Boolean).length);
