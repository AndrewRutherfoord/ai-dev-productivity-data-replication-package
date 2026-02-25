import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'neo4j-auth'

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // ignore corrupt data
  }
  return null
}

/**
 * Storage that holds the Neo4j database login details.
 * Persists to localStorage so credentials survive page reloads.
 */
export const useNeo4jAuthStore = defineStore('neo4jAuthStore', () => {
  const saved = loadFromStorage()

  const host = ref<string>(saved?.host ?? 'localhost')
  const port = ref<string>(saved?.port ?? '7687')
  const user = ref<string>(saved?.user ?? 'neo4j')
  const password = ref<string>(saved?.password ?? 'neo4j123')

  function persist() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        host: host.value,
        port: port.value,
        user: user.value,
        password: password.value,
      })
    )
  }

  watch([host, port, user, password], persist)

  return {
    host,
    port,
    user,
    password,
  }
})
