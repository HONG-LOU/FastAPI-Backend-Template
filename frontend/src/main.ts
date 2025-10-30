import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setTokensFromUrlOnce } from '@/api/client'

setTokensFromUrlOnce()
const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')


