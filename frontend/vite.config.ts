import { resolve } from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const adminMode = mode === 'admin'
  const defaultPort = adminMode ? 5174 : 5173
  const proxyTarget = env.VITE_PROXY_TARGET || `http://127.0.0.1:${env.BACKEND_PORT || (adminMode ? '8001' : '8000')}`

  return {
    appType: 'mpa',
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT || defaultPort),
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT || defaultPort),
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: adminMode ? 'dist-admin' : 'dist-public',
      rollupOptions: {
        input: resolve(__dirname, adminMode ? 'index.admin.html' : 'index.public.html'),
      },
    },
  }
})
