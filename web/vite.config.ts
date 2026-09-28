import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev server only: forward API calls through the running compose stack (change if WEB_PORT differs).
      '/api': 'http://localhost:8080',
    },
  },
})
