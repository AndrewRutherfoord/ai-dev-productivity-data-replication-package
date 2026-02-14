import axios, { type AxiosInstance, type AxiosResponse } from 'axios'

// These are the base classes for the repository pattern used for retrieving data from the backend.

export interface PaginatedResults<T> {
  total: number
  items: T[]
}

/**
 * Base class for all repositories.
 * Initializes the axios instance with the base URL for the backend.
 */
export abstract class Repository {
  protected http: AxiosInstance
  constructor(endpoint: string, baseDomain: string = '/api') {
    this.http = axios.create({ baseURL: `${baseDomain}/${endpoint}` })
  }
}

export interface ListRepository<ListType> {
  /**
   * Retrieves all items from the backend.
   */
  getAll(): Promise<AxiosResponse<ListType[]>>
}

export interface PaginatedListRepository<ListType> {
  /**
   * Retrieves all items from the backend.
   */
  getAll(): Promise<AxiosResponse<PaginatedResults<ListType[]>>>
}

export interface ItemRepository<ItemType> {
  /**
   * Retrieves an item by its id on the backend.
   * @param id Id of the item to retrieve.
   */
  getById(id: number | string): Promise<AxiosResponse<ItemType>>
}

export interface CreateItemRepository<ItemType> {
  /**
   * Creates a new item on the backend.
   *
   * @param item Data for item to create.
   */
  create(item: ItemType): Promise<AxiosResponse<ItemType>>
}

export interface UpdateItemRepository<ItemType> {
  /**
   * Updated an existing item on the backend.
   * @param id Id of the item to update.
   * @param item Data for item to update.
   */
  update(id: number | string, item: ItemType): Promise<AxiosResponse<ItemType>>
}

export interface DeleteItemRepository {
  /**
   * Deletes an item from the backend.
   * @param id Id of the item to delete.
   */
  delete(id: number | string): Promise<AxiosResponse<void>>
}
