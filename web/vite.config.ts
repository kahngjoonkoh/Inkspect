import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev server only: forward API calls to a locally running api service.
      '/api': 'http://localhost:8000',
    },
  },
})
