#!/usr/bin/env node
/**
 * verify-page — render a URL in a real browser engine and report what a reader
 * would actually see. The agent-side replacement for "open Chrome and look".
 *
 *   node scripts/verify-page.mjs <url> [options]
 *
 * Options
 *   --device "iPhone 15"      Playwright device descriptor (viewport, DPR, touch, UA).
 *                             Default: desktop 1280×900.
 *   --engine chromium|webkit  Engine. WebKit is Safari's engine (not iOS Safari —
 *                             tap-zoom and the keyboard viewport are iOS-only).
 *   --out <path.png>          Screenshot path (full page). Default: none.
 *   --select "<css>"          Print textContent of every match (e.g. [data-testid=x]).
 *   --focus "<css>"           Focus this element before measuring, to see what a tap does.
 *   --click "<selector>"      Click this first (e.g. text=Reject non-essential) — dismiss a banner.
 *   --rect "<css>"            Also print the bounding rect of this element (e.g. [role=dialog]).
 *   --full                    Screenshot the full page instead of the viewport.
 *   --wait <ms>               Extra settle time after load (default 1500).
 *
 * Always printed: final URL, HTTP status, viewport, scrollY after load, horizontal
 * overflow (scrollWidth vs viewport), console errors, and the bounding rect +
 * computed font-size of the focused element and the first submit button.
 *
 * Examples
 *   node scripts/verify-page.mjs https://www.trueight.com/ --device "iPhone 15" --out design/preview/home-iphone.png --focus textarea
 *   node scripts/verify-page.mjs http://localhost:3000/r/<id> --select '[data-testid="element-caveat"]'
 *
 * Why this exists (2026-09-02): the Chrome extension needs the founder's Chrome
 * open and cannot emulate a phone; the site sends frame-ancestors 'none' so an
 * iframe cannot either. Playwright runs headless with device emulation, every
 * session, no window. Design: audit/OPEN_WORK.md 2026-09-02 (Playwright).
 */
import { chromium, webkit, devices } from 'playwright';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const args = process.argv.slice(2);
const url = args.find((a) => !a.startsWith('--'));
if (!url) {
  console.error('usage: node scripts/verify-page.mjs <url> [--device "iPhone 15"] [--engine webkit] [--out shot.png] [--select css] [--focus css] [--click selector] [--full] [--wait ms]');
  process.exit(2);
}
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : fallback;
};
const flag = (name) => args.includes(`--${name}`);

const deviceName = opt('device');
const engineName = opt('engine', 'chromium');
const out = opt('out');
const select = opt('select');
const focusSel = opt('focus');
const clickSel = opt('click');
const rectSel = opt('rect');
const settle = Number(opt('wait', '1500'));

if (deviceName && !devices[deviceName]) {
  console.error(`unknown device "${deviceName}". Some valid names: ${Object.keys(devices).filter((d) => /iPhone 1[3-5]|Pixel 7|iPad/.test(d)).join(', ')}`);
  process.exit(2);
}

const engine = engineName === 'webkit' ? webkit : chromium;
const browser = await engine.launch();
const context = await browser.newContext(
  deviceName ? { ...devices[deviceName] } : { viewport: { width: 1280, height: 900 } },
);
const page = await context.newPage();
const consoleErrors = [];
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200));
});
page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${String(e).slice(0, 200)}`));

const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 }).catch((e) => {
  console.error(`navigation failed: ${e.message}`);
  return null;
});
await page.waitForTimeout(settle);

if (clickSel) {
  await page
    .locator(clickSel)
    .first()
    .click({ timeout: 5000 })
    .catch((e) => consoleErrors.push(`click failed: ${String(e.message).slice(0, 160)}`));
  await page.waitForTimeout(400);
}

const rect = (sel) =>
  page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return {
      x: Math.round(b.left),
      y: Math.round(b.top),
      w: Math.round(b.width),
      h: Math.round(b.height),
      fontSize: getComputedStyle(el).fontSize,
      offRight: Math.round(b.right - window.innerWidth),
    };
  }, sel);

const report = {
  url: page.url(),
  status: response?.status() ?? null,
  engine: engineName,
  device: deviceName ?? 'desktop 1280×900',
  viewport: page.viewportSize(),
  scrollY: await page.evaluate(() => window.scrollY),
  horizontalOverflowPx: await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
  submitButton: await rect('button[type="submit"]'),
};

if (focusSel) {
  await page.focus(focusSel).catch((e) => consoleErrors.push(`focus failed: ${e.message}`));
  await page.waitForTimeout(400);
  report.afterFocus = {
    active: await page.evaluate(() => document.activeElement?.tagName ?? null),
    scrollY: await page.evaluate(() => window.scrollY),
    focused: await rect(focusSel),
    submitButton: await rect('button[type="submit"]'),
  };
}

if (rectSel) {
  report.rect = await rect(rectSel);
}

if (select) {
  report.selected = await page.$$eval(select, (els) => els.map((e) => e.textContent?.trim() ?? ''));
}

report.consoleErrors = consoleErrors;

if (out) {
  const path = resolve(out);
  await mkdir(dirname(path), { recursive: true });
  await page.screenshot({ path, fullPage: flag('full') });
  report.screenshot = path;
}

console.log(JSON.stringify(report, null, 2));
await browser.close();
