import { defineConfig } from '@playwright/test';

/**
 * The workspace's smoke test (Wave 23): the complaint the wave answers, as three
 * numbers measured in a real browser.
 *
 * It runs against a deployed NinaNatur — the preview, unless SMOKE_BASE_URL names
 * another — and makes and deletes a garden of its own there, so no one else's
 * garden is touched. Chromium in both windows: what is measured is layout, and
 * the phone is a size and a touch screen, not a second engine.
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '*.e2e.ts',
  timeout: 120_000,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.SMOKE_BASE_URL ?? 'https://ninanatur-dev.w3rth.de',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop-1280x720', use: { viewport: { width: 1280, height: 720 } } },
    { name: 'phone-375x812', use: { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true } },
  ],
});
