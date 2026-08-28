import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  // The API runs as a separate process in development; in production FastAPI
  // serves this bundle from the same origin, so no proxy is involved there.
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:4000',
      '/healthz': 'http://127.0.0.1:4000',
    },
  },
  build: { outDir: 'dist', emptyOutDir: true },
});
