import './styles/tokens.css'
import './styles/base.css'
import './styles/utilities.css'
import './styles/nprogress.css'

import { createApp } from 'vue'
import App from './App.vue'
import { setupApp } from './app/setupApp'

const app = createApp(App)

setupApp(app)
app.mount('#app')
