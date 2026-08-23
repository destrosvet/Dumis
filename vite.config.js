import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [tailwindcss(), react()],
  root: resolve(__dirname, 'svjis/articles/static_src'),
  base: '/static/',
  build: {
    outDir: resolve(__dirname, 'svjis/articles/static/dist'),
    emptyOutDir: true,
    manifest: 'manifest.json',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'svjis/articles/static_src/js/main.js'),
        css: resolve(__dirname, 'svjis/articles/static_src/css/app.css'),
        homepage: resolve(__dirname, 'svjis/articles/static_src/js/homepage/index.jsx'),
      },
    },
  },
  server: {
    port: 5173,
    host: 'localhost',
  },
})
