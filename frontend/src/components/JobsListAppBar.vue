<template>
  <v-app-bar>
    <v-app-bar-title>{{ title }}</v-app-bar-title>

    <template v-slot:append>
      <v-btn
        v-if="selectedJobs.length > 0"
        variant="outlined"
        prepend-icon="mdi-refresh"
        @click="requeueSelected"
        class="mx-1"
        >Re-queue Selected</v-btn
      >
      <v-btn
        v-if="selectedJobs.length > 0"
        variant="outlined"
        prepend-icon="mdi-restart"
        @click="rerunSelected"
        class="mx-1"
        >Re-run Selected</v-btn
      >
      <v-btn
        v-if="selectedJobs.length > 0"
        variant="outlined"
        prepend-icon="mdi-delete"
        @click="deleteSelected"
        class="mx-1"
        >Delete Selected</v-btn
      >
      <v-btn icon="mdi-dots-vertical" id="menu-activator"></v-btn>
      <v-menu activator="#menu-activator">
        <v-list>
          <v-list-item @click="deleteAllJobs">
            <v-list-item-title>Delete All</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </template>
  </v-app-bar>
</template>

<script lang="ts" setup>
import { useToast } from '@/composables/useToast'
const toast = useToast()

const selectedJobs = defineModel('selectedJobs')
const emit = defineEmits(['reload'])
const props = defineProps({
  title: String as PropType<string>
})

import { JobsRepository, type JobStatus, type ListOptions } from '@/repositores/JobsRepository'

const jobsRepository = new JobsRepository()

async function deleteSelected() {
  let ok = confirm('Are you sure you want to delete the selected jobs?')
  if (ok) {
    try {
      for (let id of selectedJobs.value) {
        await jobsRepository.delete(id)
      }
      selectedJobs.value = []
      emit('reload')
      toast.success('Deleted selected jobs.')
    } catch (e) {
      console.error(e)
      toast.error('Failed to delete selected jobs.')
    }
  }
}

async function requeueSelected() {
  let ok = confirm(`Re-queue ${selectedJobs.value.length} selected jobs? Their statuses will be cleared and they will be re-added to the work queue.`)
  if (ok) {
    try {
      await jobsRepository.bulkRequeue(selectedJobs.value)
      selectedJobs.value = []
      emit('reload')
      toast.success('Re-queued selected jobs.')
    } catch (e) {
      console.error(e)
      toast.error('Failed to re-queue selected jobs.')
    }
  }
}

async function rerunSelected() {
  let ok = confirm(`Re-run ${selectedJobs.value.length} selected jobs? New jobs will be created for each.`)
  if (ok) {
    try {
      await jobsRepository.bulkRerun(selectedJobs.value)
      selectedJobs.value = []
      emit('reload')
      toast.success('Re-ran selected jobs.')
    } catch (e) {
      console.error(e)
      toast.error('Failed to re-run selected jobs.')
    }
  }
}

async function deleteAllJobs() {
  let ok = confirm(
    'Are you sure you want to delete all of the jobs? This includes failed, pending and complete jobs. The work they did will not be undone.'
  )
  if (ok) {
    try {
      await jobsRepository.deleteAll()
      emit('reload')
      toast.success('Deleted All Jobs.')
    } catch (e) {
      console.error(e)
      toast.error('Failed to delete all jobs.')
    }
  }
}
</script>
