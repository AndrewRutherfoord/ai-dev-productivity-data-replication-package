<template>
  <div>
    <jobs-list-app-bar
      title="Drill Job Statuses"
      v-model:selected-jobs="selected"
      @reload="fetchAll"
    ></jobs-list-app-bar>
    <v-container>
      <v-card :title="`Open Drill Jobs (Remaining: ${pendingJobs.total})`">
        <job-status-table
          v-if="pendingJobs && pendingJobs.items"
          :items="pendingJobs"
          v-model:options="pendingOptions"
          v-model:selected="selected"
          @delete-job="deleteJob"
          @requeue-job="requeueJob"
          @show-job-information="showDialog"
          :loading="loading"
          @reload="fetchPendingData"
        ></job-status-table>
      </v-card>
      <v-card :title="`Failed Drill Jobs`">
        <job-status-table
          v-if="failedJobs && failedJobs.items"
          :items="failedJobs"
          v-model:options="failedOptions"
          v-model:selected="selected"
          @delete-job="deleteJob"
          @rerun-job="rerunJob"
          @show-job-information="showDialog"
          :loading="loading"
          @reload="fetchFailedData"
        ></job-status-table>
      </v-card>
      <v-btn :to="{ name: 'jobs-complete-list' }" class="mt-3" block outlined color="green"
        >View Complete Jobs</v-btn
      >
    </v-container>
    <job-info-dialog v-model="dialog" :job="dialogItem"></job-info-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { useWebSocket } from '@vueuse/core'

import JobInfoDialog from '@/components/JobInfoDialog.vue'
import JobsListAppBar from '@/components/JobsListAppBar.vue'
import JobStatusTable from '@/components/JobStatusTable.vue'
import { useRepositoryList } from '@/composables/useRepositoryList'
import {
  JobsRepository,
  type JobStatus,
  type ListOptions,
  type Job
} from '@/repositores/JobsRepository'
import type { PaginatedResults } from '@/repositores/Repository'

const toast = useToast()
const jobsRepository = new JobsRepository()

// When there are fewer than MIN_PENDING_JOBS in list the list will reload.
const MIN_PENDING_JOBS = 10

const loading = ref(true)
const selected = ref<number[]>([])
const failed = ref<number>(0)

const pendingJobs = ref<PaginatedResults<Job>>({ total: 0, items: [] })
const pendingOptions = ref<ListOptions>({
  limit: 20,
  offset: 0,
  statuses: ['pending', 'started']
})

const failedJobs = ref<PaginatedResults<Job>>({ total: 0, items: [] })
const failedOptions = ref<ListOptions>({
  limit: 20,
  offset: 0,
  statuses: ['failed']
})

async function fetchData(options: ListOptions) {
  loading.value = true
  try {
    const result = await jobsRepository.getAll(options)
    return result.data
  } catch (e) {
    console.log(e)
    throw e
  } finally {
    loading.value = false
  }
}

async function fetchPendingData() {
  let result = await fetchData(pendingOptions.value)
  pendingJobs.value = result
  //  pendingJobs.value = result.map((r) => ({
  //    ...result,
  //    current_status: result.statuses.slice(-1).pop().status
  //  }))
}

async function fetchFailedData() {
  failedJobs.value = await fetchData(failedOptions.value)
}

async function fetchAll() {
  await fetchPendingData()
  await fetchFailedData()
}

onMounted(() => {
  fetchAll()
})

// Delete

async function deleteJob(id: number) {
  let ok = confirm(
    'Are you sure you want to delete this job? (This will only delete the info from the database. It will not undo the work.)'
  )
  if (ok) {
    try {
      await jobsRepository.delete(id)
      await fetchAll()
      toast.success('Deleted selected jobs.')
    } catch (e) {
      console.error(e)
    }
  }
}

async function deleteSelected() {
  let ok = confirm('Are you sure you want to delete the selected jobs?')
  if (ok) {
    try {
      for (let id of selected.value) {
        await jobsRepository.delete(id)
      }
      selected.value = []
      await fetchAll()
      toast.success('Deleted selected jobs.')
    } catch (e) {
      console.error(e)
      toast.error('Failed to delete selected jobs.')
    }
  }
}

// Re-run

async function rerunJob(id: number) {
  try {
    const result = await jobsRepository.rerun(id)
    pendingJobs.value.items.push(result.data)
    pendingJobs.value.total++
    // Remove the original job from the failed list
    failedJobs.value.items = failedJobs.value.items.filter((j) => j.id !== id)
    failedJobs.value.total--
    toast.success(`Re-queued job '${result.data.name}'.`)
  } catch (e) {
    console.error(e)
    toast.error('Failed to re-run job.')
  }
}

// Re-queue stuck jobs

async function requeueJob(id: number) {
  try {
    const result = await jobsRepository.requeue(id)
    // Update the job in the pending list with its new status
    const idx = pendingJobs.value.items.findIndex((j) => j.id === id)
    if (idx !== -1) {
      pendingJobs.value.items[idx] = result.data
    }
    toast.success(`Re-queued job '${result.data.name}'.`)
  } catch (e) {
    console.error(e)
    toast.error('Failed to re-queue job.')
  }
}

// Job Info Dialog
const dialog = ref(false)
const dialogItem = ref()

function showDialog(item: Job) {
  dialogItem.value = item
  dialog.value = true
}

// Job Status Updates - Websocket
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const { status } = useWebSocket(`${wsProtocol}//${window.location.host}/api/jobs/statuses`, { onMessage })

let messageBuffer: { job: Job; job_status: JobStatus }[] = []

function addStatus(job: Job, status: JobStatus) {
  let idx = pendingJobs.value.items.findIndex((j) => j.id === job.id)
  console.log(idx, pendingJobs.value.total)
  if (status.status === 'failed') {
    failedJobs.value.items.push({ ...job, statuses: [status] })
    pendingJobs.value.items.splice(idx, 1)
    pendingJobs.value.total--
  }

  if (idx === -1) {
    pendingJobs.value.items.push({ ...job, statuses: [status] })
  } else if (status.status === 'complete') {
    pendingJobs.value.items.splice(idx, 1)
    pendingJobs.value.total--
  } else {
    try {
      if (pendingJobs.value.items[idx].statuses) {
        pendingJobs.value.items[idx].statuses.push(status)
      } else {
        pendingJobs.value.items[idx].statuses = [status]
      }
    } catch (e) {
      console.error(e)
      console.error(pendingJobs.value.items[idx])
    }
  }

  // Fetch more data if we have less than 5 items and more than 5 total
  if (
    pendingJobs.value.items.length - failed.value < MIN_PENDING_JOBS &&
    pendingJobs.value.total > MIN_PENDING_JOBS
  ) {
    fetchPendingData()
  }
}

let isProcessing = false
function processMessages() {
  if (isProcessing || loading.value) return
  isProcessing = true
  while (messageBuffer.length > 0) {
    let message = messageBuffer.shift()
    if (message) {
      let job: Job = message.job
      let jobStatus: JobStatus = message.job_status
      addStatus(job, jobStatus)
    }
  }
  isProcessing = false
}

function onMessage(ws: WebSocket, event: MessageEvent) {
  let message = JSON.parse(event.data)
  console.log(message)

  if (message.job_status.status === 'complete') {
    toast.success(`Drilling of '${message.job.name}' is complete.`)
  } else if (message.job_status.status === 'started') {
    toast.success(`Drilling of '${message.job.name}' started.`)
  } else if (message.job_status.status === 'error') {
    toast.error(message.message)
  } else if (message.job_status.status === 'warning') {
    toast.warn(message.message)
  }

  messageBuffer.push(message)
  processMessages()
}
</script>

<style scoped></style>
