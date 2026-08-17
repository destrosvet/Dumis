import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [tailwindcss()],
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
      },
    },
  },
  server: {
    port: 5173,
    host: 'localhost',
  },
})
