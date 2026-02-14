export type CursorPageResult<T> = {
  items?: T[]
  total?: number
  current_page?: string | null
  previous_page?: string | null
  next_page?: string | null
}
