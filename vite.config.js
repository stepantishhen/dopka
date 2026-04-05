import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// В Docker backend доступен как http://backend:8000; локально — http://127.0.0.1:8000
const backendProxyTarget =
  process.env.DOCKER_BACKEND_PROXY || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    open: false,
    watch: {
      usePolling: true,
      interval: 1000,
    },
    proxy: {
      '/api': {
        target: backendProxyTarget,
        changeOrigin: true,
      },
    },
  },
})

