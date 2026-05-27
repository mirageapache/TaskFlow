/**
 * 主題切換工具。
 *
 * 同步策略：
 * - 後端 UserProfile.theme 為來源真實值（'light' | 'dark' | 'system'）
 * - 本機 localStorage 為 fallback，讓 App 啟動到 fetchUser() 完成前不會閃白屏
 * - 套用方式：toggle <html>.dark class，PrimeVue (darkModeSelector: '.dark')
 *   與 Tailwind (darkMode: 'class') 皆吃這個 class
 *
 * 規格：.doc/taskflow-api_doc.md §8（偏好設定）
 */

export type ThemePreference = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme_preference'

function isDarkPreferred(theme: ThemePreference): boolean {
  if (theme === 'dark') return true
  if (theme === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** 套用主題到 <html>，並寫入 localStorage 供下次啟動讀回。 */
export function applyTheme(theme: ThemePreference): void {
  document.documentElement.classList.toggle('dark', isDarkPreferred(theme))
  localStorage.setItem(STORAGE_KEY, theme)
}

/** App 啟動時呼叫一次：讀 localStorage 套用主題，沒值則走 system。 */
export function initThemeFromStorage(): void {
  const stored = localStorage.getItem(STORAGE_KEY) as ThemePreference | null
  applyTheme(stored ?? 'system')
}
