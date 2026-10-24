import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5180, strictPort: true },
  preview: { port: 5180 },
  build: { chunkSizeWarningLimit: 700 }, // recharts pesa ~400 kB; aceptable en un panel interno
})
