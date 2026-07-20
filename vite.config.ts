import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const config = {
  base: '/head-neck-tnm-survival/',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    exclude: ['**/node_modules/**', '**/dist/**', '**/._*'],
  },
}

export default defineConfig(config)
