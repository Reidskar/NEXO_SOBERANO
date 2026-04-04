import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Backend URL: env var → localhost fallback
  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8000'

  return {
    plugins: [react()],

    // Make VITE_BACKEND_URL available in code as import.meta.env.VITE_BACKEND_URL
    define: {
      __BACKEND_URL__: JSON.stringify(backendUrl),
    },

    server: {
      port: 3000,
      host: true,
      // Proxy to backend in dev — all API + WS calls go to backendUrl
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: backendUrl.replace('http', 'ws'),
          ws: true,
          changeOrigin: true,
        },
        '/health': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },

    build: {
      outDir: 'dist',
      sourcemap: mode === 'development',
      rollupOptions: {
        output: {
          manualChunks: {
            'globe':  ['react-globe.gl'],
            'vendor': ['react', 'react-dom', 'react-router-dom'],
          },
        },
      },
    },

    preview: {
      port: 4173,
      proxy: {
        '/api': { target: backendUrl, changeOrigin: true },
        '/ws':  { target: backendUrl.replace('http', 'ws'), ws: true },
      },
    },
  }
})
