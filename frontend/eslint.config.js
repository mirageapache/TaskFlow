/**
 * ESLint flat config（ESLint 9 介面）。
 *
 * 規格：.doc/taskflow-frontend.md — Phase 2 「CI 靜態分析」
 *
 * 採用的 preset：
 *  - eslint:recommended         JS 基本規則
 *  - typescript-eslint/recommended  TS 規則（含 no-unused-vars 等）
 *  - eslint-plugin-vue (vue3-recommended)  Vue SFC 規則
 *  - @vue/eslint-config-typescript        把上述兩者橋接起來，避免規則衝突
 *
 * 注意：
 *  - test / setup 檔放寬 `any` / `non-null-assertion` 等規則，避免 mock 寫死攔截器
 *  - 排除 dist / coverage / node_modules
 */
import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import vueTsConfig from '@vue/eslint-config-typescript'
import tseslint from 'typescript-eslint'
import globals from 'globals'

export default tseslint.config(
  {
    ignores: ['dist/', 'coverage/', 'node_modules/', '*.d.ts'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs['flat/recommended'],
  vueTsConfig(),
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // Vue 3 + TS 專案常見放寬
      'vue/multi-word-component-names': 'off',
      // 允許底線開頭的暫不使用變數（型別占位 / 解構忽略）
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' },
      ],
      // 純樣式類規則關閉：本專案 SFC 風格與 vue3-recommended 預設不一致，
      // 把 CI 焦點留給真正的 bug-catching 規則（no-unused-vars、no-explicit-any 等）。
      // 後續若導入 Prettier 統一格式可再考慮打開。
      'vue/html-self-closing': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/attributes-order': 'off',
      'vue/first-attribute-linebreak': 'off',
    },
  },
  {
    // 測試 / setup 檔：mock 與斷言常用 any、ts-ignore
    files: ['src/tests/**/*.{ts,vue}', 'src/**/*.test.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
    },
  },
)
