// src/composables/useFetchList.ts
import { ref, onMounted, type Ref } from 'vue'
import type { AxiosResponse } from 'axios'
import type { BaseListRepository } from '@/repositores/BaseListRepository'

/**
 * Composable that calls the getAll method of a BaseRepository and returns the items, loading state, and errors.
 *
 * @param repositoryInstance instance of BaseRepository on which the getAll method is called
 */
export function useRepositoryList<ListType>(
  repository: BaseListRepository<ListType>,
  options: Ref<any> = ref({}),
  instant: boolean = true
) {
  const items = ref<ListType[]>([])
  const loading = ref(true)
  const error = ref<string | null>(null)

  /**
   * calls the getAll method of the repository and sets the items ref to the response data. Sets loading before and after request.
   * If an error occurs, sets error to the error message.
   *
   * @returns List of items from the repository
   * @throws AxiosError if an error occurs on the request
   */
  const fetchItems = async () => {
    loading.value = true
    try {
      const response: AxiosResponse<ListType[]> = await repository.getAll(options.value) 
      items.value = response.data
      loading.value = false
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An unknown error occurred'
      loading.value = false
      throw err
    }
  }

  // Fetch items on mount
  onMounted(fetchItems)

  return {
    items,
    loading,
    error,
    fetchItems
  }
}
