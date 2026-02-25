import {
  Repository,
  type ListRepository,
} from './Repository'

/**
 * Repository for managing job configuration files in the backend.
 */
export class DatabaseBackupsRepository extends Repository implements ListRepository<Object> {
  constructor() {
    super('files/db-exports/')
  }

  async getAll() {
    return this.http.get(``)
  }
}
