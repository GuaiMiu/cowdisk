import { AppError, normalizeError } from '@/api/errors'

export type UiErrorInfo = {
  title: string
  message: string
  retryable: boolean
  code?: number | string
}

const codeTitleMap: Record<number, string> = {
  400: '请求参数错误',
  401: '登录状态失效',
  403: '权限不足',
  404: '资源不存在',
  408: '请求超时',
  409: '数据冲突',
  422: '参数校验失败',
  429: '请求过于频繁',
  500: '服务暂时不可用',
  502: '网关异常',
  503: '服务维护中',
  504: '网关超时',
}

export const mapToUiError = (error: unknown, fallbackTitle = '操作失败'): UiErrorInfo => {
  const normalized = normalizeError(error)
  const code = normalized.code
  const title =
    (typeof code === 'number' ? codeTitleMap[code] : '') ||
    (normalized.transient ? '网络波动' : fallbackTitle)
  const message = normalized.message || '请稍后重试'
  return {
    title,
    message,
    retryable: !!normalized.transient || code === 408 || code === 429,
    code,
  }
}

export const withErrorCode = (text: string, code?: number | string) => {
  if (code === undefined || code === null || code === '') {
    return text
  }
  return `${text} (E${String(code)})`
}

export const toAppError = (error: unknown) => {
  return normalizeError(error) as AppError
}
