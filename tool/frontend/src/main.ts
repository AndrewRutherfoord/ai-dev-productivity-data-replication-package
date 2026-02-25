import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import { install as VueMonacoEditorPlugin } from '@guolao/vue-monaco-editor'

// Vuetify
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import Notifications from '@kyvg/vue3-notification'

import axios from 'axios'


axios.defaults.baseURL = '/'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(VueMonacoEditorPlugin, {
  paths: {
    // The recommended CDN config
    vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.43.0/min/vs'
  }
})

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light'
  }
})
app.use(vuetify)
app.use(Notifications)

app.mount('#app')
