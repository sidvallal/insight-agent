import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the browser talks to /api, and Vite forwards it to FastAPI
// (so there are no CORS problems and streaming works the same as in production).
export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 1200 },   // the lazy Plotly chunk is large by design
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    globals: true,
  },
});