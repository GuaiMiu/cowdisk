export type ResponseModel<T> = {
  code: number
  message: string
  data: T | T[] | null
}
