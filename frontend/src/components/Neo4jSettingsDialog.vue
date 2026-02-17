<template>
  <v-dialog v-model="visible" max-width="450px">
    <v-card title="Neo4j Connection">
      <v-card-text>
        <v-text-field v-model="form.host" label="Host" density="compact" class="mb-2" />
        <v-text-field v-model="form.port" label="Port" density="compact" class="mb-2" />
        <v-text-field v-model="form.user" label="Username" density="compact" class="mb-2" />
        <v-text-field
          v-model="form.password"
          label="Password"
          density="compact"
          :type="showPassword ? 'text' : 'password'"
          :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
          @click:append-inner="showPassword = !showPassword"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="visible = false">Cancel</v-btn>
        <v-btn variant="flat" color="primary" @click="save">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useNeo4jAuthStore } from '@/stores/neo4jStore'

const visible = defineModel<boolean>({ default: false })
const showPassword = ref(false)
const store = useNeo4jAuthStore()

const form = reactive({
  host: store.host,
  port: store.port,
  user: store.user,
  password: store.password,
})

watch(visible, (open) => {
  if (open) {
    form.host = store.host
    form.port = store.port
    form.user = store.user
    form.password = store.password
  }
})

function save() {
  store.host = form.host
  store.port = form.port
  store.user = form.user
  store.password = form.password
  visible.value = false
}
</script>
