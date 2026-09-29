import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// The gardeners' own clock. CI runs in UTC, where local time and UTC are the
// same thing, and a test of a page that reads a `datetime-local` field could
// not tell the two apart (review of doc 122, 2026-09-28).
process.env.TZ = 'Europe/Berlin';

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', globals: true },
});
