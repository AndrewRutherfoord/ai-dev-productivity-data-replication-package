<template>
  <v-data-table
    v-if="options !== undefined"
    :items="items.items"
    :headers="headers"
    :loading="loading"
    :items-per-page="options.limit"
    show-select
    v-model="selected"
    item-value="id"
  >
    <template v-slot:item.status="{ item }">
      <v-progress-circular
        v-if="getJobStatus(getRawJob(item)) === 'started'"
        color="green"
        indeterminate
        size="25"
        class="me-2"
      ></v-progress-circular>
      <v-chip :color="getJobStatusColor(getRawJob(item))" text-color="white">
        {{ getJobStatus(getRawJob(item)) }}
      </v-chip>
      <!-- Tooltip which shows error message if job status is failed. -->
      <v-tooltip
        :text="getJobStatusObj(getRawJob(item))?.message"
        v-if="getJobStatus(getRawJob(item)) === 'failed' && getJobStatusObj(getRawJob(item))?.message"
        max-width="200px"
      >
        <template v-slot:activator="{ props }">
          <v-icon v-bind="props" class="ms-2">mdi-information-outline</v-icon>
        </template>
      </v-tooltip>
    </template>
    <template v-slot:item.timestamp="{ item }">
      {{ getJobTimestamp(getRawJob(item)) }}
    </template>
    <template v-slot:item.button="{ item }">
      <v-btn color="primary" size="small" class="mx-2" @click="emit('show-job-information', getRawJob(item))"
        >View</v-btn
      >
      <v-btn
        v-if="getJobStatus(getRawJob(item)) === 'failed'"
        color="warning"
        size="small"
        class="mx-2"
        @click="emit('rerun-job', getRawJob(item).id)"
        >Re-run</v-btn
      >
      <v-btn
        v-if="getJobStatus(getRawJob(item)) === 'started'"
        color="warning"
        size="small"
        class="mx-2"
        @click="emit('requeue-job', getRawJob(item).id)"
        >Re-queue</v-btn
      >
      <v-btn color="red-darken-2" size="small" class="mx-2" @click="emit('delete-job', getRawJob(item).id)"
        >Delete</v-btn
      >
    </template>
    <template v-slot:bottom>
      <v-pagination
        :length="Math.ceil(items.total / options.limit)"
        @update:model-value="updatePage"
        :model-value="page"
      ></v-pagination>
    </template>
  </v-data-table>
</template>

<script setup lang="ts">
import type { Job, JobStatus } from '@/repositores/JobsRepository'
import type { Pagination } from '@/repositores/Pagination'
import type { PaginatedResults } from '@/repositores/Repository'
import { computed } from 'vue'

const headers = [
  { title: 'Name', value: 'name' },
  { title: 'Status', value: 'status' },
  { title: 'timestamp', key: 'timestamp' },
  {
    title: '',
    key: 'button'
  }
]

const props = defineProps({
  items: {
    type: Object as () => PaginatedResults<Job>,
    required: true
  },
  loading: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['delete-job', 'rerun-job', 'requeue-job', 'show-job-information', 'reload'])

const selected = defineModel<number[]>('selected')

// Pagination

const options = defineModel<Pagination>('options')

function updatePage(value: number) {
  if (options.value == undefined) return
  options.value.offset = (value - 1) * options.value.limit
  console.log(options.value)
  emit('reload')
}

const page = computed(() => {
  if (options.value == undefined) return 1
  return Math.ceil(options.value?.offset / options.value.limit) + 1
})

// Render Functions

function getRawJob(item: any): Job {
  return item?.raw ?? item
}

function getJobStatusObj(job: Job): JobStatus | undefined {
  if (!Array.isArray(job.statuses) || job.statuses.length === 0) {
    return undefined
  }

  return job.statuses.reduce((latest, current) => {
    return current.timestamp > latest.timestamp ? current : latest
  })
}

function getJobStatus(job: Job) {
  let jobStatus = getJobStatusObj(job)

  let status = 'pending'
  if (jobStatus !== undefined) {
    status = jobStatus.status
  }
  return status
}

function getJobTimestamp(job: Job) {
  let jobStatus = getJobStatusObj(job)

  if (jobStatus !== undefined) {
    let date = Date.parse(jobStatus.timestamp)
    return new Date(date).toLocaleString()
  }
  return ''
}

function getJobStatusColor(job: Job) {
  let status = getJobStatus(job)
  switch (status) {
    case 'pending':
      return 'primary'
    case 'started':
      return 'secondary'
    case 'complete':
      return 'success'
    case 'failed':
      return 'error'
    case 'retrying':
      return 'warning'
  }
}
</script>

<style scoped></style>

