import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'

import App from './App.vue'
import { initSentry } from './lib/sentry'
import router from './router'
import { initThemeFromStorage } from './utils/theme'
import './assets/main.css'

// 在 mount 前套用主題，避免從 localStorage 讀取 dark 設定時的閃白屏
initThemeFromStorage()

const app = createApp(App)
initSentry({ app, router })
app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: { preset: Aura, options: { darkModeSelector: '.dark' } },
})
app.use(ToastService)
app.mount('#app')
