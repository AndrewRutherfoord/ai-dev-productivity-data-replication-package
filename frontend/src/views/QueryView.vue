<template>
  <v-app-bar>
    <v-app-bar-title>Query Graph Database</v-app-bar-title>

    <v-btn :href="neo4jBrowserUrl">Open Neo4j Browser</v-btn>
    <v-btn v-if="result" variant="outlined" prepend-icon="mdi-download" @click="saveToFile">Download Data</v-btn>
  </v-app-bar>

  <vue-splitter initial-percent="20" style="height: 100%">
    <template #left-pane>
      <file-tree-sidebar title="Saved Queries" subtitle="Click on one to open it and then execute it."
        @link-clicked="openFile" @delete-file="deleteQuery" :data="files" @create-file="openNewFile"
        :is-loading="filesIsLoading"></file-tree-sidebar>
    </template>
    <template #right-pane>
      <div class="d-flex justify-space-between">
        <v-breadcrumbs class="py-2" :items="currentFile ? currentFile.split('/') : ['new-query.cql']"></v-breadcrumbs>
        <v-btn class="mt-1 me-3" size="compact" variant="text" @click="saveQuery" icon="mdi-content-save"
          :disabled="!unsavedChanges"></v-btn>
      </div>
      <hr>
      <v-container fluid class="rounded-0">
        <!-- Query Bar -->
        <cypher-code-mirror ref="editor" class="border-sm" v-model="content" />
        <div class="my-2">
          <v-btn color="blue" @click="executeQuery">Execute Query
            <v-tooltip activator="parent" location="bottom">Execute query (Ctrl + Q)</v-tooltip>
          </v-btn>
          <v-btn density="compact" variant="plain" icon="mdi-content-save" class="ms-2" @click="saveQuery"></v-btn>
          <v-btn density="compact" variant="plain" icon="mdi-information-outline" class="ms-2"></v-btn>
        </div>



        <!-- Query Error Alert -->
        <v-alert v-if="error" type="error">{{ error }}</v-alert>
        <hr class="my-2">

        <!-- Query Results -->
        <v-data-table v-if="result !== null" :items="result" :headers="tableHeaders" :loading="loading">
          <template v-slot:item.actions="{ item }">
            <v-btn color="primary" size="small" class="mx-2" @click="showDialog(item)">View</v-btn>
          </template>
        </v-data-table>

      </v-container>
      <query-data-dialog v-model:data="dialogData" v-model:visibility="dialog"></query-data-dialog>
    </template>
  </vue-splitter>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from 'axios';

import { useNeo4j } from '@/composables/useNeo4j';
import { useSaveData } from '@/composables/useSaveData';
import { useAxios } from '@vueuse/integrations/useAxios'
import { useMagicKeys } from '@vueuse/core'
import { useToast } from '@/composables/useToast';
import { useRepositoryList } from '@/composables/useRepositoryList';
import { useRoute, useRouter } from 'vue-router';

import VueSplitter from '@rmp135/vue-splitter'
import FileTreeSidebar from '../components/FileTreeList.vue'
import CypherCodeMirror from '../components/CypherCodeMirror.vue';
import QueryDataDialog from '../components/QueryDataDialog.vue'
import { QueryFileRepository } from '@/repositores/FileRepository';
import useConfirmLeavePage from '@/composables/useConfirmLeavePage';

const router = useRouter()
const route = useRoute()

const queriesRepository = new QueryFileRepository();

const toast = useToast();

// Neo4j Browser URL from environment variable
const neo4jBrowserUrl = import.meta.env.VITE_NEO4J_BROWSER_URL || 'http://127.0.0.1:7474/';

const dialog = ref(false);
const dialogData = ref<string>()

// ----- Editor -----
const editor = ref()
const currentFile = ref<string | null>(null);
const content = ref<string>("");

// Most recently saved content. Used to compare with current content to see if it has changed.
const savedContent = ref<string>("");

const unsavedChanges = computed(() => content.value !== savedContent.value)

onMounted(async () => {
  if (route.query.file) {
    // Open the file if `file` query parameter is set.
    currentFile.value = route.query.file as string
    await openFile(route.query.file as string)
  } else {
    content.value = "";
    savedContent.value = content.value;
  }
})

// ----- Executing Neo4j Queries -----

const { runQuery, error, loading, result, headers } = useNeo4j();

const tableHeaders = computed(() => {
  let result = headers.value?.map((h) => ({ title: h, key: h }));
  result?.push({ title: "", key: 'actions' })
  return result
})

async function executeQuery() {
  if (!editor.value.getQuery()) {
    return
  }
  let query = editor.value.getQuery()
  console.log(query)
  await runQuery(query)
}

// ----- Key Binds -----

const keys = useMagicKeys()
const ctrlQ = keys['Ctrl+Q']

watch(ctrlQ, (v) => {
  if (v) {
    executeQuery()
  }
})

// ----- Download Data -----

const jsonifiedData = computed(() => {
  return JSON.stringify(result.value, null, 2)
})
const { saveToFile, filename } = useSaveData(jsonifiedData, "query-data.json")

function showDialog(item) {
  dialogData.value = item
  dialog.value = true
}

// ----- Confirm Leave when unsaved changes -----

const confirmLeaveMessage = "You have unsaved changes. Are you sure you want to leave ?";

// Inverse of unsaved changes. If true, the page can be left without showing the dialog.
const leavable = computed(() => !unsavedChanges.value)

// Shows the confirm leave dialog when there are unsaved changes.
useConfirmLeavePage(confirmLeaveMessage, leavable)

// ----- Saved Queries -----

const { items: files, loading: filesIsLoading, fetchItems: getQueryFiles } = useRepositoryList(queriesRepository);

/**
 * On selection of file in sidebar, load the file and set the content.
 * @param path Path of the file to load.
 */
async function openFile(path: string) {
  try {
    let response = await queriesRepository.getById(path)
    console.log(response)
    // content.value = response.data;
    editor.value.setValue(response.data)
    savedContent.value = content.value;
    currentFile.value = path;
    router.replace({ query: { file: path } })
  } catch (e) {
    if (axios.isAxiosError(e)) {
      if (e.response?.status === 404) {
        toast.error("File not found.")
      } else {
        toast.error("Failed to load file.")
      }
    } else {
      toast.error("Failed to load file.")
      console.error(e)
    }
    openNewFile();
  }
}
/**
 * Clears the editor content and sets back to initial boilerplate.
 * Sets current file name to null to indicate that a new file is being created.
 */
async function openNewFile() {
  editor.value.setValue("")
  currentFile.value = null;
  router.replace({})
}

async function saveQuery() {
  let filename = currentFile.value;
  if (filename === null) {
    filename = prompt("What do you want to name the query file?")
  }
  if (filename == null) {
    // User cancelled the save.
    return
  }
  let response = await queriesRepository.update(filename, { content: content.value })

  if (response.status === 200) {
    toast.success("Saved query to new file.")
  } else if (response.status === 201) {
    toast.success("Updated saved query file.")
  }

  currentFile.value = filename;
  savedContent.value = content.value;

}

async function deleteQuery(path: string) {
  let ok = await confirm(`Are you sure you want to delete '${path}'?`)
  try {
    if (ok) {
      let response = await queriesRepository.delete(path)
      toast.success("COnfiguration file deleted.")
      // If the deleted file is the current file, open a clean new file.
      if (path === currentFile.value) {
        openNewFile()
      }
      await getQueryFiles()
    } else {
      toast.warn("Deletion cancelled.")
    }
  } catch (e) {
    console.error(e)
    toast.error("Failed to delete query.")
  }
}

</script>