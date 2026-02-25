<template>
  <v-app-bar>
    <v-app-bar-title>Drill Config Editor</v-app-bar-title>
    <template v-slot:append>
      <v-btn class="mx-2" variant="outlined" color="green" @click="checkConfig" prepend-icon="mdi-check">Check
        Config</v-btn>
      <v-btn variant="outlined" @click="executeDrillJob">Execute Drill Job</v-btn>
    </template>
  </v-app-bar>

  <vue-splitter initial-percent="20" style="height: 100%">
    <template #left-pane>
      <file-tree-sidebar title="Saved Configs" subtitle="Click on one to open it and then execute it."
        @link-clicked="openFile" @delete-file="deleteConfiguration" @create-file="openNewFile" :data="files"
        :is-loading="filesIsLoading"></file-tree-sidebar>
    </template>
    <template #right-pane>
      <div class="d-flex justify-space-between">
        <v-breadcrumbs class="py-2" :items="currentFile ? currentFile.split('/') : ['new-file.json']"></v-breadcrumbs>
        <v-btn class="mt-1 me-3" size="compact" variant="text" @click="saveConfiguration" icon="mdi-content-save"
          :disabled="!unsavedChanges"></v-btn>
      </div>
      <hr />
      <!-- {{ currentFile }} -->
      <v-sheet height="100vh">
        <Editor v-model="content" @save="saveConfiguration"></Editor>
      </v-sheet>
    </template>
  </vue-splitter>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios, { AxiosError } from 'axios'
import yaml from 'js-yaml'

import { useRoute, useRouter } from 'vue-router'
import { useRepositoryList } from '@/composables/useRepositoryList'
import { useYamlValidation } from '@/composables/useYamlValidation'
import useConfirmLeavePage from '@/composables/useConfirmLeavePage'
import { useToast } from '@/composables/useToast'

import { ConfigurationFileRepository } from '../repositores/FileRepository'

import FileTreeSidebar from '../components/FileTreeList.vue'
import VueSplitter from '@rmp135/vue-splitter'

import initial from '../assets/initial.yaml?raw'
import schema from '../../../schemas/schema.json?raw'
import Editor from '../components/Editor.vue'
import { JobsRepository } from '@/repositores/JobsRepository'

const router = useRouter()
const route = useRoute()

const configurationsRepository = new ConfigurationFileRepository()
const jobsRepository = new JobsRepository()

const toast = useToast()

// Editor content.
const currentFile = ref<string | null>(null)
const content = ref<string>('')

// Most recently saved content. Used to compare with current content to see if it has changed.
const savedContent = ref<string>('')

const unsavedChanges = computed(() => content.value !== savedContent.value)

onMounted(async () => {
  if (route.query.file) {
    // Open the file if `file` query parameter is set.
    currentFile.value = route.query.file as string
    await openFile(route.query.file as string)
  } else {
    content.value = initial
    savedContent.value = content.value
  }
})

// ----- Validation of config -----

const { valid, error, validate } = useYamlValidation(schema, content)

/**
 * Checks if the current configuration is valid.
 */
function checkConfig() {
  if (validate()) {
    toast.success('Configuration is valid!')
  } else {
    toast.error('Configuration Invalid.', error.value ? error.value : '')
  }
}

// ----- Execution of Drill Job -----

/**
 * Sends job config file to backend. Should then be sent to workers to drill repositories.
 * Checks config before sending. If invalid, halts and creates error toast.
 */
async function executeDrillJob() {
  if (!validate()) {
    toast.error(error.value ? error.value : 'Configuration is invalid.')
    return
  }

  try {
    let { data } = await jobsRepository.createList(yaml.load(content.value));
    toast.success(`${data.length} job${data.length > 1 ? 's have' : ' has'} been created successfully. Proceed to the job status page to see the status.`)
  } catch (e) {
    toast.error('Could not create jobs.')
    console.error(e)
  }
}

// ----- Confirm Leave when unsaved changes -----

const confirmLeaveMessage = 'You have unsaved changes. Are you sure you want to leave ?'

// Inverse of unsaved changes. If true, the page can be left without showing the dialog.
const leavable = computed(() => !unsavedChanges.value)

// Shows the confirm leave dialog when there are unsaved changes.
useConfirmLeavePage(confirmLeaveMessage, leavable)

// ----- Saving Configurations -----

// List of all the configuration files.
const {
  items: files,
  loading: filesIsLoading,
  fetchItems: getConfigFilesList
} = useRepositoryList(configurationsRepository)

/**
 * On selection of file in sidebar, load the file and set the content.
 * @param path Path of the file to load.
 */
async function openFile(path: string) {
  try {
    let response = await configurationsRepository.getById(path)
    console.log(response)
    content.value = response.data
    savedContent.value = content.value
    currentFile.value = path
    router.replace({ query: { file: path } })
  } catch (e) {
    if (axios.isAxiosError(e)) {
      if (e.response?.status === 404) {
        toast.error('File not found.')
      } else {
        toast.error('Failed to load file.')
      }
    } else {
      toast.error('Failed to load file.')
    }
    openNewFile()
  }
}

/**
 * Clears the editor content and sets back to initial boilerplate.
 * Sets current file name to null to indicate that a new file is being created.
 */
async function openNewFile() {
  content.value = initial
  currentFile.value = null
  router.replace({})
}

/**
 * Saves the current configuration file.
 */
async function saveConfiguration() {
  let filename = currentFile.value
  if (filename === null) {
    filename = prompt('What do you want to name the configuration file?')
  }
  if (filename == null) {
    // User cancelled the save.
    return
  }
  let response = await configurationsRepository.update(filename, { content: content.value })

  if (response.status === 200) {
    toast.success('Saved configuration to new file.')
  } else if (response.status === 201) {
    toast.success('Updated saved configuration file.')
  }

  currentFile.value = filename
  savedContent.value = content.value

  await getConfigFilesList()
}

async function deleteConfiguration(path: string) {
  let ok = await confirm(`Are you sure you want to delete '${path}'?`)
  try {
    if (ok) {
      let response = await configurationsRepository.delete(path)
      toast.success('COnfiguration file deleted.')
      // If the deleted file is the current file, open a clean new file.
      if (path === currentFile.value) {
        openNewFile()
      }
      await getConfigFilesList()
    } else {
      toast.warn('Deletion cancelled.')
    }
  } catch (e) {
    console.error(e)
    toast.error('Failed to delete query.')
  }
}
</script>
