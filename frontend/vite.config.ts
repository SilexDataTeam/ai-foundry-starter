import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/stream_events': 'http://localhost:8000',
      '/feedback': 'http://localhost:8000',
      '/generate_chat_title': 'http://localhost:8000',
      '/chats': 'http://localhost:8000',
      '/config': 'http://localhost:8000',
    },
  },
})
