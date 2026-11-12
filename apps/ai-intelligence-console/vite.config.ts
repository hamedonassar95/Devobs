import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const appRoot = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': resolve(appRoot, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
    build: {
      // Three.js is a single upstream module, loaded only by the lazy 3D views (about 141 KiB gzipped).
      chunkSizeWarningLimit: 600,
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              { name: 'three-vendor', test: /node_modules[\\/]three[\\/]/, priority: 2 },
              { name: 'firebase-vendor', test: /node_modules[\\/](firebase|@firebase|@grpc)[\\/]/, priority: 1 },
              { name: 'vendor', test: /node_modules[\\/]/, priority: 0 },
            ],
          },
        },
      },
    },
  };
});
