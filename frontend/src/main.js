import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router' // Import the router we just made

createApp(App).use(router).mount('#app')