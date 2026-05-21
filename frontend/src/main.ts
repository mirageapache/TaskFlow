import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'

import App from './App.vue'
import { initSentry } from './lib/sentry'
import router from './router'
import './assets/main.css'

const app = createApp(App)
initSentry({ app, router })
app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: { preset: Aura, options: { darkModeSelector: '.dark' } },
})
app.use(ToastService)
app.mount('#app')
