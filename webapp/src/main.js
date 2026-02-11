import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'
import './assets/main.css'
import { registerSW } from 'virtual:pwa-register'

registerSW({ immediate: true })

createApp(App).use(router).mount('#app')
