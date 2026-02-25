import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import neo4j, { Driver, Session } from 'neo4j-driver'
import { useNeo4jAuthStore } from '@/stores/neo4jStore'
import { storeToRefs } from 'pinia'

export function useNeo4j() {
  const driver = ref<Driver | null>(null)
  const session = ref<Session | null>(null)
  const error = ref<any>(null)
  const loading = ref(false)

  const result = ref<any>(null)
  const headers = ref<string[] | null>(null)
  const notifications = ref<any>(null)

  const store = useNeo4jAuthStore()
  const { host, port, user, password } = storeToRefs(store)

  // Initialize the driver and session
  const initialize = () => {
    close()

    const scheme = 'neo4j' // <-- adjust once, don’t auto-detect
    const url = `${scheme}://${host.value}:${port.value}`
    console.log(`Connecting to Neo4j at ${url} with user ${user.value}`)

    driver.value = neo4j.driver(
      url,
      neo4j.auth.basic(user.value, password.value)
    )

    session.value = driver.value.session()
  }

  // Close the session and driver
  const close = () => {
    if (session.value) {
      session.value.close()
    }
    if (driver.value) {
      driver.value.close()
    }
  }

  // Reconnect when credentials change
  watch([host, port, user, password], initialize)

  // Run a Cypher query
  const runQuery = async (query: string, parameters = {}) => {
    loading.value = true
    error.value = null
    result.value = null
    headers.value = null

    try {
      if (!session.value) {
        throw new Error('Session not initialized')
      }

      const resultSet = await session.value.run(query, parameters)
      result.value = resultSet.records
      notifications.value = resultSet.summary.notifications
      result.value = resultSet.records.map((record) => record.toObject())

      if (resultSet.records.length > 0) {
        headers.value = resultSet.records[0].keys
      }

      loading.value = false
      return resultSet
    } catch (err) {
      loading.value = false
      error.value = err
      throw err
    }
  }

  /**
   * Initiates a backup of the Neo4j database.
   * @param filename The cypher file's name where the backup should be written
   */
  const backupDatabase = async (filename: string) => {
    return await runQuery(`CALL apoc.export.cypher.all("${filename}", 
        {format: "cypher-shell",useOptimizations: {type: "UNWIND_BATCH", unwindBatchSize: 20}}) 
        YIELD file, batches, source, format, nodes, relationships, properties, time, rows, batchSize 
        RETURN file, batches, source, format, nodes, relationships, properties, time, rows, batchSize;`)
  }

  /**
   * Clears the Neo4j database of all data. 
   */
  const clearDatabase = async () => {
    await runQuery(`MATCH (n) DETACH DELETE n`)
    await runQuery(`CALL apoc.schema.assert({},{},true) YIELD label, key RETURN *`)
  }

  /**
   * Restores a backup from the cypher file. The file needs to site in the neo4j_import folder in
   * the volumes of the Neo4j container.
   * 
   * @param filename Filename from which to lead the backup.
   */
  const restoreDatabaseBackup = async (filename: string) => {
    return await runQuery(`CALL apoc.cypher.runFile("${filename}")`)
  }

  onMounted(() => {
    // On mount initiates a connection to the Neo4j db.
    initialize()
  })

  onBeforeUnmount(() => {
    // Disconnects from Neo4j db before unloading component.
    close()
  })

  return {
    initialize,
    close,
    runQuery,
    clearDatabase,
    backupDatabase,
    restoreDatabaseBackup,
    error,
    loading,
    result,
    headers,
    notifications
  }
}
