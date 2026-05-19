import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
  const rawTarget = env.VITE_API_TARGET || 'http://localhost:8001';
  const apiTarget = rawTarget.includes('127.0.0.1:8002') || rawTarget.includes('localhost:8002')
    ? 'http://127.0.0.1:8000'
    : rawTarget;
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
          '/api': {
            target: apiTarget,
            changeOrigin: true,
            secure: false,
          },
          '/inventory': {
            target: apiTarget,
            changeOrigin: true,
            secure: false,
          },
          '/notifications': {
            target: apiTarget,
            changeOrigin: true,
            secure: false,
          },
          '/alerts': {
            target: apiTarget,
            changeOrigin: true,
            secure: false,
          }
        }
      },
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
