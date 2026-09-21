#!/usr/bin/env node
/**
 * The plan's contact sheet (doc 95): every sheet garden at 12, 40 and 120 m
 * and with the sun map, drawn by Chromium from the app's own components.
 *
 *   npm run plan:sheet                    light mode, into sheet-out/light/
 *   npm run plan:sheet -- --dark          dark mode, into sheet-out/dark/
 *   npm run plan:sheet -- --check         both modes, compared with sheet/baseline.json
 *   npm run plan:sheet -- --update        both modes, recorded in sheet/baseline.json
 *   npm run plan:sheet -- --timing        the paint budget: the city at 40 m, CPU slowed ×4
 *   npm run plan:sheet -- --timing --update   …and recorded
 *   npm run plan:sheet -- --theme draft-sketch [--dark] [--timing]
 *                                         another theme, into sheet-out/<theme>/ — looked
 *                                         at, never recorded: the record is Technisch's
 *
 * `--check` exits 1 naming every changed cell, and leaves its new image in
 * sheet-out/ to be looked at. The images are never committed; the record is.
 */
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { cpus, platform } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from '@playwright/test';

import { composeSheet, paintMs, pixelHash } from './sheet-pixels.mjs';

const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(FRONTEND, 'sheet-out');
const BASELINE = join(FRONTEND, 'sheet', 'baseline.json');
const PORT = 5197;
const ORIGIN = `http://127.0.0.1:${PORT}`;
const WIDTH = 360;
const HEIGHT = 270;
const GARDENS = [
  { id: 'small', title: 'Reihenhausgarten' },
  { id: 'farmyard', title: 'Hof' },
  { id: 'city', title: 'Blockinnenhof' },
];
const COLUMNS = [
  { span: 12, sun: false, label: '12 m' },
  { span: 40, sun: false, label: '40 m' },
  { span: 120, sun: false, label: '120 m' },
  { span: 40, sun: true, label: '40 m, Sonne' },
];
const TIMING_RUNS = 5;
const CPU_SLOWDOWN = 4;

const flags = new Set(process.argv.slice(2));
const themeAt = process.argv.indexOf('--theme');
const THEME = themeAt > 0 ? (process.argv[themeAt + 1] ?? 'technisch') : 'technisch';
const RECORDED = THEME === 'technisch';
if (!RECORDED && flags.has('--check')) {
  console.error(`the record is Technisch's; ${THEME} is drawn to be looked at — drop --check`);
  process.exit(2);
}
// Draft Sketch changes its level of detail at 144 and 238 m across a cell (doc 97),
// and a fourth garden shows what the first three do not (doc 98).
const SHOWN = RECORDED ? COLUMNS : [...COLUMNS, { span: 200, sun: false, label: '200 m' }, { span: 400, sun: false, label: '400 m' }];
const ROWS = RECORDED ? GARDENS : [...GARDENS, { id: 'vocabulary', title: 'Musterblatt' }];
const folder = (mode) => (RECORDED ? join(OUT, mode) : join(OUT, THEME, mode));
const modes = flags.has('--check') || flags.has('--update') ? ['light', 'dark'] : [flags.has('--dark') ? 'dark' : 'light'];

/** The sheet's own Vite, on its own port: another dev server may be running here. */
async function serve() {
  const server = spawn('npx', ['vite', '--host', '127.0.0.1', '--port', String(PORT), '--strictPort', '--logLevel', 'error'], {
    cwd: FRONTEND, stdio: ['ignore', 'inherit', 'inherit'],
  });
  for (let i = 0; i < 120; i += 1) {
    try {
      if ((await fetch(`${ORIGIN}/sheet.html`)).ok) return server;
    } catch {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  server.kill();
  throw new Error('the sheet server did not start');
}

const cellName = (garden, column) => `${garden}-${column.span}${column.sun ? '-sonne' : ''}`;

async function load(page, garden, column, theme = THEME) {
  const query = new URLSearchParams({ garden, span: String(column.span), sun: column.sun ? '1' : '0', w: String(WIDTH), h: String(HEIGHT) });
  if (theme !== 'technisch') query.set('theme', theme);
  await page.goto(`${ORIGIN}/sheet.html?${query}`);
  await page.waitForFunction(() => document.body.dataset.ready === 'yes');
}

/** Every cell in one mode: its image written, its pixels hashed, the sheet composed. */
async function renderMode(browser, mode) {
  const context = await browser.newContext({ colorScheme: mode, deviceScaleFactor: 1, viewport: { width: WIDTH + 40, height: HEIGHT + 40 } });
  const page = await context.newPage();
  await mkdir(folder(mode), { recursive: true });
  const rows = [];
  const hashes = {};
  for (const garden of ROWS) {
    const cells = [];
    for (const column of SHOWN) {
      await load(page, garden.id, column);
      const png = await page.locator('.sheet-cell').screenshot();
      const name = cellName(garden.id, column);
      await writeFile(join(folder(mode), `${name}.png`), png);
      hashes[`${mode}/${name}`] = await pixelHash(page, png);
      cells.push({ png });
    }
    rows.push({ title: garden.title, cells });
  }
  await writeFile(join(folder(mode), 'sheet.png'), await composeSheet(page, { mode, rows, columns: SHOWN }));
  await context.close();
  return hashes;
}

/** The paint budget's measure: the city, a hundred elements, on a slowed CPU. */
async function timing(browser) {
  const context = await browser.newContext({ deviceScaleFactor: 1, viewport: { width: WIDTH + 40, height: HEIGHT + 40 } });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: CPU_SLOWDOWN });
  const measure = async (theme) => {
    const runs = [];
    for (let i = 0; i < TIMING_RUNS; i += 1) {
      await load(page, 'city', COLUMNS[1], theme);
      runs.push(Math.round(await paintMs(page)));
    }
    const sorted = [...runs].sort((a, b) => a - b);
    return { runs, median_ms: sorted[Math.floor(sorted.length / 2)] };
  };
  const mine = await measure(THEME);
  // A style that is not Technisch is measured against it in the same run: the
  // machine and the day move both numbers, and it is the pair that means
  // something (doc 99).
  const plain = RECORDED ? null : await measure('technisch');
  await context.close();
  return { cell: 'city-40', cpu_slowdown: CPU_SLOWDOWN, ...mine,
           ...(plain === null ? {} : { technisch_ms: plain.median_ms }),
           machine: `${platform()} ${cpus()[0]?.model ?? ''}`.trim() };
}

async function readBaseline() {
  try {
    return JSON.parse(await readFile(BASELINE, 'utf8'));
  } catch {
    return { cells: {} };
  }
}

async function main() {
  const server = await serve();
  const browser = await chromium.launch();
  let failed = false;
  try {
    const baseline = await readBaseline();
    const hashes = {};
    if (!flags.has('--timing') || flags.has('--check') || (flags.has('--update') && RECORDED)) {
      for (const mode of modes) Object.assign(hashes, await renderMode(browser, mode));
      console.log(`sheet written: ${modes.map((m) => join(folder(m), 'sheet.png')).join(', ')}`);
    }
    if (flags.has('--check')) {
      if (baseline.chromium && baseline.chromium !== browser.version()) {
        console.log(`note: the record was taken with Chromium ${baseline.chromium}, this is ${browser.version()}`);
      }
      const changed = Object.keys(hashes).filter((cell) => baseline.cells[cell] !== hashes[cell]);
      failed = changed.length > 0;
      console.log(failed ? `changed: ${changed.join(', ')}` : `all ${Object.keys(hashes).length} cells as recorded`);
    }
    const budget = flags.has('--timing') ? await timing(browser) : null;
    if (budget !== null) {
      console.log(`paint: median ${budget.median_ms} ms over ${budget.runs.join(', ')} (CPU ×${CPU_SLOWDOWN})`);
      if (budget.technisch_ms) {
        console.log(`against Technisch's ${budget.technisch_ms} ms in the same run: `
          + `${(budget.median_ms / budget.technisch_ms).toFixed(1)}×`);
      }
      const recorded = RECORDED ? baseline.timing : baseline.budgets?.[THEME];
      if (recorded?.median_ms) {
        console.log(`recorded: ${recorded.median_ms} ms (${recorded.machine ?? 'another machine'})`);
      }
    }
    if (flags.has('--update')) {
      const next = { ...baseline, chromium: browser.version(), cells: Object.keys(hashes).length ? hashes : baseline.cells };
      // Technisch's is the guard a change is measured against; another style's
      // is what that style costs, which is a fact about it, not a threshold.
      if (budget !== null && RECORDED) next.timing = budget;
      if (budget !== null && !RECORDED) next.budgets = { ...baseline.budgets, [THEME]: budget };
      await writeFile(BASELINE, `${JSON.stringify(next, null, 2)}\n`);
      console.log(`recorded in ${join('sheet', 'baseline.json')}`);
    }
  } finally {
    await browser.close();
    server.kill();
  }
  process.exit(failed ? 1 : 0);
}

await main();
