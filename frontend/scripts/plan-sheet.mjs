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

async function load(page, garden, column) {
  const query = new URLSearchParams({ garden, span: String(column.span), sun: column.sun ? '1' : '0', w: String(WIDTH), h: String(HEIGHT) });
  await page.goto(`${ORIGIN}/sheet.html?${query}`);
  await page.waitForFunction(() => document.body.dataset.ready === 'yes');
}

/** Every cell in one mode: its image written, its pixels hashed, the sheet composed. */
async function renderMode(browser, mode) {
  const context = await browser.newContext({ colorScheme: mode, deviceScaleFactor: 1, viewport: { width: WIDTH + 40, height: HEIGHT + 40 } });
  const page = await context.newPage();
  await mkdir(join(OUT, mode), { recursive: true });
  const rows = [];
  const hashes = {};
  for (const garden of GARDENS) {
    const cells = [];
    for (const column of COLUMNS) {
      await load(page, garden.id, column);
      const png = await page.locator('.sheet-cell').screenshot();
      const name = cellName(garden.id, column);
      await writeFile(join(OUT, mode, `${name}.png`), png);
      hashes[`${mode}/${name}`] = await pixelHash(page, png);
      cells.push({ png });
    }
    rows.push({ title: garden.title, cells });
  }
  await writeFile(join(OUT, mode, 'sheet.png'), await composeSheet(page, { mode, rows, columns: COLUMNS }));
  await context.close();
  return hashes;
}

/** The paint budget's measure: the city, a hundred elements, on a slowed CPU. */
async function timing(browser) {
  const context = await browser.newContext({ deviceScaleFactor: 1, viewport: { width: WIDTH + 40, height: HEIGHT + 40 } });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: CPU_SLOWDOWN });
  const runs = [];
  for (let i = 0; i < TIMING_RUNS; i += 1) {
    await load(page, 'city', COLUMNS[1]);
    runs.push(Math.round(await paintMs(page)));
  }
  await context.close();
  const sorted = [...runs].sort((a, b) => a - b);
  return { cell: 'city-40', cpu_slowdown: CPU_SLOWDOWN, runs, median_ms: sorted[Math.floor(sorted.length / 2)], machine: `${platform()} ${cpus()[0]?.model ?? ''}`.trim() };
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
    if (!flags.has('--timing') || flags.has('--check') || flags.has('--update')) {
      for (const mode of modes) Object.assign(hashes, await renderMode(browser, mode));
      console.log(`sheet written: ${modes.map((m) => join('sheet-out', m, 'sheet.png')).join(', ')}`);
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
    if (budget !== null) console.log(`paint: median ${budget.median_ms} ms over ${budget.runs.join(', ')} (CPU ×${CPU_SLOWDOWN})`);
    if (flags.has('--update')) {
      const next = { ...baseline, chromium: browser.version(), cells: Object.keys(hashes).length ? hashes : baseline.cells };
      if (budget !== null) next.timing = budget;
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
