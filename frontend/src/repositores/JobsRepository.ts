import type { AxiosResponse } from 'axios'
import {
  Repository,
  type ItemRepository,
  type DeleteItemRepository,
  type CreateItemRepository,
  type PaginatedListRepository
} from './Repository'
import type { Pagination } from './Pagination'

type status = 'failed' | 'pending' | 'complete' | 'started'

export interface JobStatus {
  job_id: number
  status: status[]
  timestamp: string
}

export interface Job {
  id: number
  name: string
  data: Object
  statuses: JobStatus[]
}


export type ListOptions = Pagination & {
  statuses?: status[]
}

/**
 * Repository for managing job configuration files in the backend.
 */
export class JobsRepository
  extends Repository
  implements
    PaginatedListRepository<Job>,
    ItemRepository<Job>,
    CreateItemRepository<Object>,
    DeleteItemRepository
{
  constructor() {
    super('jobs/')
  }

  async getAll(options: ListOptions = { limit: 10, offset: 0 }) {
    return this.http.get(``, { params: options, paramsSerializer: { indexes: null } })
  }

  async getById(id: string | number): Promise<AxiosResponse<Job>> {
    return this.http.get(`${id}`)
  }

  async create(data: Object): Promise<AxiosResponse<string>> {
    return this.http.post(``, data)
  }

  async createList(data: any) : Promise<AxiosResponse<Job[]>> {
    return this.http.post(``, data);
  }

  async delete(id: string | number): Promise<AxiosResponse<void>> {
    return this.http.delete(`${id}`)
  }

  async deleteAll(): Promise<AxiosResponse<void>> {
    return this.http.delete(``)
  }
}
