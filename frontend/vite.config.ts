import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/** Draft Sketch's own folder of the build (doc 97), which the server hands
 *  out on the preview only: nothing of Warren Davison's is served in public
 *  before he has seen it. `ninanatur/web/delivery.py` holds the other half. */
const DRAFT_SKETCH = '/themes/draft-sketch/';
const isDraftSketch = (path: string): boolean => path.replaceAll('\\', '/').includes(DRAFT_SKETCH);

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
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Never inline an asset as a `data:` URI: the CSP allows images from the
    // site itself only, so an inlined one would not be drawn at all.
    assetsInlineLimit: 0,
    rollupOptions: {
      output: {
        chunkFileNames: (chunk) =>
          chunk.moduleIds.some(isDraftSketch) ? 'assets/draft-sketch/[name]-[hash].js' : 'assets/[name]-[hash].js',
        assetFileNames: (asset) =>
          asset.originalFileNames.some(isDraftSketch)
            ? 'assets/draft-sketch/[name]-[hash][extname]'
            : 'assets/[name]-[hash][extname]',
      },
    },
  },
});
