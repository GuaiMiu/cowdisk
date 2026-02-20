import './styles/tokens.css'
import './styles/base.css'
import './styles/utilities.css'
import './styles/layout-shell.css'
import './styles/nprogress.css'

import { createApp } from 'vue'
import App from './App.vue'
import { setupApp } from './app/setupApp'
import { initTheme } from './composables/useTheme'

const app = createApp(App)

initTheme()

setupApp(app).then(() => {
  app.mount('#app')
})
