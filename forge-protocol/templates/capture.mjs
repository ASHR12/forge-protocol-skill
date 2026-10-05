#!/usr/bin/env node
// forge-protocol capture template: stills and walkthrough frames from a running web build, plus MANIFEST.md.
// Copied to tools/capture.mjs by `forge.py init --stack web`; edit freely for the project.
//
//   node tools/capture.mjs --url http://localhost:5173 [--views tools/views.json] [--size 1920x1080] [--dpr 1]
//        [--out artifacts/stills] [--frames 10 --walk-ms 8000 --frames-out artifacts/walkthrough-frames]
//        [--clock fixed] [--seed 7] [--build-id <id>] [--channel chrome] [--color-scheme dark]
//
// views.json: [{"name": "hero", "path": "/", "hash": "#hero", "eval": "window.__forgeSetView?.('hero')",
//               "waitMs": 500, "fullPage": false}]
// Page hooks (optional): set window.__FORGE_READY__ = true once the scene is loaded; expose
// window.__forgeSetView(name) for camera presets or UI states. Needs: npm i -D playwright
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const args = parseArgs(process.argv.slice(2));
if (args.help || !args.url) {
  console.log('usage: node capture.mjs --url <url> [--views views.json] [--size WxH] [--dpr N] [--out dir] ' +
    '[--frames N --walk-ms MS --walk-path P --walk-hash H --walk-eval JS --frames-out dir] [--clock fixed|real] [--seed N] [--build-id id] ' +
    '[--channel chrome] [--color-scheme light|dark] [--settle-ms MS] [--ready-timeout-ms MS] [--freeze] ' +
    '[--fail-on-console-error]');
  process.exit(args.help ? 0 : 2);
}

let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  console.error('capture.mjs: Playwright is not installed. Run: npm i -D playwright && npx playwright install chromium');
  process.exit(2);
}

const [width, height] = String(args.size || '1920x1080').split('x').map(Number);
if (!width || !height) fail(`--size must look like 1920x1080, got ${args.size}`);
const dpr = Number(args.dpr || 1);
const outDir = args.out || 'artifacts/stills';
const framesDir = args['frames-out'] || 'artifacts/walkthrough-frames';
const settleMs = Number(args['settle-ms'] ?? 1500);
const readyTimeoutMs = Number(args['ready-timeout-ms'] ?? 30000);
const fixedClock = args.clock === 'fixed';
const views = args.views ? JSON.parse(await readFile(args.views, 'utf8')) : [{ name: 'home' }];
if (!Array.isArray(views) || views.length === 0) fail('--views must be a non-empty JSON array');

const consoleErrors = [];
const browser = await chromium.launch(args.channel ? { channel: args.channel } : {});
let exitCode = 0;
try {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: dpr,
    colorScheme: args['color-scheme'] || 'light',
    locale: 'en-US',
    timezoneId: 'UTC',
    reducedMotion: args.freeze ? 'reduce' : 'no-preference',
  });
  if (args.seed !== undefined) {
    await context.addInitScript((seed) => {
      let s = Number(seed) >>> 0;
      Math.random = () => {
        s = (s + 0x6d2b79f5) >>> 0;
        let t = s;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    }, args.seed);
  }
  const page = await context.newPage();
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(`console: ${msg.text()}`); });
  page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`));
  if (fixedClock) {
    // install() alone keeps fake time flowing in real time; pauseAt() makes runFor() the only clock.
    const t0 = new Date('2026-01-01T00:00:00Z');
    await page.clock.install({ time: t0 });
    await page.clock.pauseAt(new Date(t0.getTime() + 1000));
  }

  await mkdir(outDir, { recursive: true });
  const rows = [];
  for (const [i, view] of views.entries()) {
    const file = `still-${String(i + 1).padStart(2, '0')}.png`;
    await open(page, view.path, view.hash);
    if (view.eval) await page.evaluate(view.eval);
    await pause(page, Number(view.waitMs ?? 500));
    await page.screenshot({
      path: path.join(outDir, file),
      fullPage: Boolean(view.fullPage),
      animations: args.freeze ? 'disabled' : 'allow',
      caret: 'hide',
    });
    rows.push(`| ${file} | ${args['build-id'] || 'n/a'} | ${width * dpr}x${height * dpr} | ${view.name || '-'} | ${new Date().toISOString()} |`);
    console.log(`captured ${file} (${view.name || 'view'})`);
  }
  await writeFile(path.join(outDir, 'MANIFEST.md'), [
    '# Capture manifest', '', `Captured by tools/capture.mjs from ${args.url}.`, '',
    '| still | build | size | view | captured |', '| --- | --- | --- | --- | --- |', ...rows, '',
  ].join('\n'));

  const frames = Number(args.frames || 0);
  if (frames > 0) {
    await mkdir(framesDir, { recursive: true });
    const walk = views[0];
    await open(page, args['walk-path'] ?? walk.path, args['walk-hash'] ?? walk.hash);
    if (args['walk-eval']) await page.evaluate(args['walk-eval']);
    const step = Math.max(1, Math.round(Number(args['walk-ms'] || 6000) / frames));
    for (let f = 1; f <= frames; f += 1) {
      await pause(page, step);
      await page.screenshot({ path: path.join(framesDir, `frame-${String(f).padStart(2, '0')}.png`), caret: 'hide' });
    }
    console.log(`captured ${frames} walkthrough frames into ${framesDir}`);
  }
  if (consoleErrors.length) {
    await writeFile(path.join(outDir, 'console-errors.log'), consoleErrors.join('\n') + '\n');
    console.warn(`warning: ${consoleErrors.length} console/page errors; see ${path.join(outDir, 'console-errors.log')}`);
    if (args['fail-on-console-error']) exitCode = 3;
  }
} catch (err) {
  console.error(`capture.mjs: ${err.message}`);
  exitCode = 1;
} finally {
  await browser.close();
}
process.exit(exitCode);

async function open(page, routePath, hash) {
  const url = new URL(routePath || '', args.url);
  if (hash) url.hash = hash;
  await page.goto(url.toString(), { waitUntil: 'load' });
  await page.evaluate(async () => { if (document.fonts) await document.fonts.ready; return true; });
  const hasReadyFlag = await page.evaluate(() => typeof window.__FORGE_READY__ !== 'undefined');
  if (hasReadyFlag) {
    if (fixedClock) {
      const deadline = Date.now() + readyTimeoutMs;
      while (!(await page.evaluate(() => window.__FORGE_READY__ === true))) {
        if (Date.now() > deadline) throw new Error('window.__FORGE_READY__ never became true');
        await page.clock.runFor(100);
      }
    } else {
      await page.waitForFunction(() => window.__FORGE_READY__ === true, null, { timeout: readyTimeoutMs });
    }
  }
  await pause(page, settleMs);
}

async function pause(page, ms) {
  if (fixedClock) await page.clock.runFor(ms);
  else await page.waitForTimeout(ms);
  if (!fixedClock) await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith('--')) out[key] = true;
    else { out[key] = next; i += 1; }
  }
  return out;
}

function fail(message) {
  console.error(`capture.mjs: ${message}`);
  process.exit(2);
}
