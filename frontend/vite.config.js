import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';
export default defineConfig({
    plugins: [vue()],
    server: {
        port: 5173,
        host: true
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, 'src')
        }
    }
});
