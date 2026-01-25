export type ResponseModel<T> = {
  code: number
  msg: string
  data: T | T[] | null
  time: string
}
