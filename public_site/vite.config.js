import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5174 },
  preview: {
    port: 8001,
    host: '0.0.0.0',
    allowedHosts: ['elanarcocapital.com', 'www.elanarcocapital.com', 'localhost', '127.0.0.1'],
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three', '@react-three/fiber', '@react-three/drei'],
          gsap:  ['gsap', '@gsap/react'],
          react: ['react', 'react-dom', 'react-router-dom'],
        }
      }
    }
  }
})
