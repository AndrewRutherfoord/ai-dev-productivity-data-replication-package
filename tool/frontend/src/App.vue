<template>
  <v-card>
    <v-layout>
      <SidebarNav @open-neo4j-settings="showNeo4jSettings = true"></SidebarNav>
      <v-main min-height="100vh">
        <RouterView />
      </v-main>

    </v-layout>
  </v-card>
  <Neo4jSettingsDialog v-model="showNeo4jSettings" />
  <Notifications class="ma-3" position="bottom right" />
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useWebSocket } from '@vueuse/core'
import { useToast } from '@/composables/useToast';
import SidebarNav from './components/SidebarNav.vue'
import Neo4jSettingsDialog from './components/Neo4jSettingsDialog.vue'
import { Notifications } from '@kyvg/vue3-notification';

const showNeo4jSettings = ref(false)
const messages = ref<string[]>([])

const toast = useToast()

// function onMessage(ws: WebSocket, event: MessageEvent) {
//   let message = JSON.parse(event.data)
//   messages.value.push(message)
//   console.log(message)

//   if (message.job_status.status === 'complete') {
//     toast.success(`Drilling of '${message.job.name}' is complete.`)
//   } else if (message.job_status.status === 'started') {
//     toast.success(`Drilling of '${message.job.name}' started.`)
//   } else if (message.job_status.status === 'error') {
//     toast.error(message.message)
//   } else if (message.job_status.status === 'warning') {
//     toast.warn(message.message)
//   }
// }

// const { status, data, send, open, close } = useWebSocket('ws://127.0.0.1:8000/notifications', { onMessage })


</script>