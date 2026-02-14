import axios from 'axios'

export class AppError extends Error {
  code?: number
  details?: unknown
  transient?: boolean

  constructor(message: string, code?: number, details?: unknown, transient = false) {
    super(message)
    this.name = 'AppError'
    this.code = code
    this.details = details
    this.transient = transient
  }
}

export type ValidationErrorItem = {
  loc?: Array<string | number>
  msg?: string
  type?: string
}

const formatValidationErrors = (details: ValidationErrorItem[]) => {
  if (!details.length) {
    return '请求参数校验失败'
  }
  return details
    .map((item) => {
      const loc = Array.isArray(item.loc) ? item.loc.join('.') : ''
      const msg = item.msg || '参数错误'
      return loc ? `${loc}: ${msg}` : msg
    })
    .join('；')
}

export function normalizeError(error: unknown): AppError {
  if (error instanceof AppError) {
    return error
  }

  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const axiosCode = error.code || ''
    const transient =
      !error.response ||
      axiosCode === 'ERR_NETWORK' ||
      axiosCode === 'ECONNABORTED' ||
      axiosCode === 'ETIMEDOUT' ||
      status === 408 ||
      status === 429 ||
      (typeof status === 'number' && status >= 500)
    const data = error.response?.data as
      | {
          code?: number
          msg?: string
          detail?: ValidationErrorItem[]
          data?: string[]
        }
      | undefined

    if (status === 422) {
      if (Array.isArray(data?.detail)) {
        return new AppError(formatValidationErrors(data.detail), 422, data.detail, false)
      }
      if (Array.isArray(data?.data)) {
        return new AppError(data.data.join('；') || '请求参数校验失败', 422, data.data, false)
      }
    }

    if (data && typeof data === 'object' && 'msg' in data) {
      return new AppError(data.msg || '请求失败', data.code ?? status, data, transient)
    }

    if (axiosCode === 'ECONNABORTED' || axiosCode === 'ETIMEDOUT') {
      return new AppError('请求超时', status, data, true)
    }
    if (axiosCode === 'ERR_NETWORK' || !error.response) {
      return new AppError('连接中断', status, data, true)
    }

    return new AppError(error.message || '请求失败', status, data, transient)
  }

  return new AppError('请求失败')
}
