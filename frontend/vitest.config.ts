import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'url'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      // 量測 src/ 下的應用碼；排除設定、bootstrap、純型別、Phase 1 placeholder
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/main.ts',
        'src/App.vue',
        'src/env.d.ts',
        'src/types/**',
        'src/router/**', // route 宣告為主，guard 邏輯有 navigation.test.ts
        'src/tests/**',
        // Phase 2/3 才填滿邏輯的 placeholder view
        'src/views/AiCenterView.vue',
        'src/views/OAuthCallbackView.vue',
        'src/views/SettingsView.vue',
      ],
      thresholds: {
        lines: 80,
        statements: 80,
        branches: 80,
        functions: 70,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
