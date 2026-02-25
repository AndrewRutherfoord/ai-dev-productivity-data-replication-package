import type { AxiosResponse } from 'axios'
import {
  Repository,
  type ListRepository,
  type ItemRepository,
  type DeleteItemRepository,
  type UpdateItemRepository
} from './Repository'

export type SaveFileContent = {
  content: string
}

/**
 * Repository for managing job configuration files in the backend.
 */
export class FileRepository
  extends Repository
  implements
    ListRepository<Object>,
    ItemRepository<string>,
    UpdateItemRepository<SaveFileContent>,
    DeleteItemRepository
{
  constructor(endpoint: string) {
    super(`files/${endpoint}`)
  }

  async getAll(): Promise<AxiosResponse<Object[]>> {
    return this.http.get(``)
  }

  async getById(id: string): Promise<AxiosResponse<string>> {
    return this.http.get(`${id}`)
  }

  /**
   * Creates or updates a file in the backend.
   *
   * @param path Location of the file in the backend.
   * @param content Contents of the file.
   * @returns Response from the backend.
   */
  async update(path: string, content: SaveFileContent): Promise<AxiosResponse<SaveFileContent>> {
    return this.http.post(`${path}`, content)
  }

  async delete(id: string): Promise<AxiosResponse<void>> {
    return this.http.delete(`${id}`)
  }
}

class YamlFileRepository extends FileRepository {

  /**
   * Creates or updates a YAML file on the backend.
   * Appends .yaml to the file name if it is not already present.
   *
   * @param path Location of the file in the backend.
   * @param content Contents of the file.
   * @returns Response from the backend.
   */
  async update(path: string, content: SaveFileContent): Promise<AxiosResponse<SaveFileContent>> {
    if (!(path.endsWith('.yaml') || path.endsWith('.yml'))) {
      path = path + '.yaml'
    }
    return super.update(path, content)
  }
}

export class ConfigurationFileRepository extends YamlFileRepository {
  constructor() {
    super(`configs/`)
  }

}

export class QueryFileRepository extends YamlFileRepository {
  constructor() {
    super(`queries/`)
  }

}
