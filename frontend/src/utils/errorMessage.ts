import { AppError, normalizeError } from '@/api/errors'
import { resolveCodeMessage } from '@/errors/codeMap'
import { i18n } from '@/i18n'

export type UiErrorInfo = {
  title: string
  message: string
  retryable: boolean
  code?: number | string
}

const isRetryableError = (error: AppError) => {
  if (error.transient) {
    return true
  }
  if (error.code === 100004 || error.code === 200013 || error.code === 200023) {
    return true
  }
  if (error.httpStatus === 408 || error.httpStatus === 429) {
    return true
  }
  if (typeof error.httpStatus === 'number' && error.httpStatus >= 500) {
    return true
  }
  return false
}

export const mapToUiError = (
  error: unknown,
  fallbackTitle = i18n.global.t('common.operationFailed'),
): UiErrorInfo => {
  const normalized = normalizeError(error)
  const code = normalized.code ?? normalized.httpStatus
  const title = resolveCodeMessage(normalized.code) ||
    (normalized.transient ? i18n.global.t('common.networkIssue') : fallbackTitle)
  const message = normalized.message || i18n.global.t('common.retryLater')
  return {
    title,
    message,
    retryable: isRetryableError(normalized),
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
