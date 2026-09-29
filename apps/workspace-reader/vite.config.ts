import { reactRouter } from '@react-router/dev/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), reactRouter()],
  ssr: { noExternal: ['fumadocs-core', 'fumadocs-ui', '@fumadocs/base-ui'] },
  server: { host: '127.0.0.1', port: 8790, strictPort: true },
});
