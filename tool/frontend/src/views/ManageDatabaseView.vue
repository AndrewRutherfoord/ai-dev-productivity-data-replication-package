<template>
  <div>
    <v-app-bar>
      <v-app-bar-title>Manage Neo4j Database</v-app-bar-title>
    </v-app-bar>
    <v-container fluid class="rounded-0">
      <v-row v-if="neo4jLoading">
        <v-col>
          <v-alert type="warning" :title="loadingAlert.title"
            :text="loadingAlert.content" variant="outlined"
            prominent>
            <template v-slot:prepend>
              <v-progress-circular size="30" width="5" color="red" indeterminate></v-progress-circular>
            </template>
          </v-alert>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <neo4j-database-overview ref="overviewCard"></neo4j-database-overview>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-card>
            <file-tree-list title="Database Images" subtitle="Here you can load database backups" :data="files"
              :is-loading="filesIsLoading" create-new-tooltip="Backup Current Database State"
              @linkClicked="restoreBackup" @createFile="backupCurrentDatabase"></file-tree-list>
          </v-card>
        </v-col>
        <v-col>
          <v-card title="Settings">
            <v-list>
              <v-list-item value="notifications">
                <template v-slot:prepend="{ isActive }">
                  <v-list-item-action start>
                    <v-btn color="red" @click="clearDatabase"><v-icon>mdi-delete</v-icon></v-btn>
                  </v-list-item-action>
                </template>

                <v-list-item-title>Clear Database</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { useRepositoryList } from '@/composables/useRepositoryList'
import { DatabaseBackupsRepository } from '@/repositores/DatabaseBackupsRepository'
import FileTreeList from '@/components/FileTreeList.vue'
import { computed, onMounted, ref } from 'vue'
import { useNeo4j } from '@/composables/useNeo4j'
import { useToast } from '@/composables/useToast'
import Neo4jDatabaseOverview from '@/components/Neo4jDatabaseOverview.vue'
import useConfirmLeavePage from '@/composables/useConfirmLeavePage'

const repository = new DatabaseBackupsRepository()

const toast = useToast()
const { items, loading: filesIsLoading, fetchItems: getFiles } = useRepositoryList(repository)

const neo4jLoading = ref(false)
useConfirmLeavePage(
  'The database backup is still loading. Are you sure you want to leave?',
  neo4jLoading,
  true
)

// TODO: Move credentials to store.
const { runQuery, clearDatabase: clearNeo4jDatabase, backupDatabase: backupNeo4jDatabase, restoreDatabaseBackup: restoreNeo4jBackup } = useNeo4j()

const files = computed(() => {
  if (items.value === null || items.value == undefined) {
    return null
  }
  return items.value
  // return (items.value)['neo4j_import']
})

const overviewCard = ref()

type LoadingAlert = {
  title: string,
  content?:string
}
const loadingAlert = ref<LoadingAlert>({
  title: "",
  content: "",
})

function reload() {
  getFiles()
  overviewCard.value.getData()
}

async function clearDatabase() {
  let ok = await confirm('Are you sure you want to clear the database?')
  if (!ok) {
    return
  }
  try {
    neo4jLoading.value = true;
    loadingAlert.value = {
      title: "Clearing database"
    }
    await clearNeo4jDatabase()
    neo4jLoading.value = false;
    toast.success('Database cleared.')
    reload()
  } catch (err) {
    console.log(err)
    toast.error('Failed to clear database.')
  }
}

async function restoreBackup(path: string) {
  let ok = await confirm(
    `Are you sure you want to restore '${path}'? This will first delete EVERYTHING in the database.`
  )
  if (!ok) {
    return
  }
  try {
    loadingAlert.value = {
      title: "Restoring Database Backup",
      content: "For big backups this can take some time. Please be patient and don't leave the page."
    }
    neo4jLoading.value = true

    await clearNeo4jDatabase()
    toast.warn('Database cleared. Loading backup now.')

    await restoreNeo4jBackup(path)

    neo4jLoading.value = false
    toast.success('Database wiped and restored from backup.')

    reload()
  } catch (err) {
    console.log(err)
    toast.error('Failed to restore backup.')
  }
}

async function backupCurrentDatabase() {
  let filename = prompt('What do you want to name the backup file?')
  if (filename == null || filename === '') {
    // User cancelled the save.
    return
  }
  if (!filename.endsWith('.cypher')) {
    filename += '.cypher'
  }
  try {
    loadingAlert.value = {
      title: "Creating Backup",
      content: "Please wait and don't leave the page."
    }
    neo4jLoading.value =  true;
    await backupNeo4jDatabase(filename)
    toast.success('Backup created.')
    neo4jLoading.value = false;
    await reload()
  } catch (err) {
    console.log(err)
    toast.error('Failed to create backup.')
  }
}
</script>
