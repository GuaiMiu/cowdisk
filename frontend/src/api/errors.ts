import axios from 'axios'
import { resolveCodeMessage } from '@/errors/codeMap'
import { i18n } from '@/i18n'

export class AppError extends Error {
  code?: number
  httpStatus?: number
  details?: unknown
  transient?: boolean

  constructor(
    message: string,
    code?: number,
    details?: unknown,
    transient = false,
    httpStatus?: number,
  ) {
    super(message)
    this.name = 'AppError'
    this.code = code
    this.httpStatus = httpStatus
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
    return i18n.global.t('apiErrors.validationFailed')
  }
  return details
    .map((item) => {
      const loc = Array.isArray(item.loc) ? item.loc.join('.') : ''
      const msg = item.msg || i18n.global.t('apiErrors.paramInvalid')
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
          message?: string
          detail?: ValidationErrorItem[]
          data?: string[]
        }
      | undefined

    if (status === 422) {
      if (Array.isArray(data?.detail)) {
        return new AppError(formatValidationErrors(data.detail), 100002, data.detail, false, status)
      }
      if (Array.isArray(data?.data)) {
        return new AppError(
          data.data.join('；') || i18n.global.t('apiErrors.validationFailed'),
          100002,
          data.data,
          false,
          status,
        )
      }
    }

    if (data && typeof data === 'object' && 'message' in data) {
      const base = (data.message || '').trim()
      const localized = resolveCodeMessage(data.code)
      const message = localized || base || i18n.global.t('apiErrors.requestFailed')
      return new AppError(message, data.code, data, transient, status)
    }

    if (axiosCode === 'ECONNABORTED' || axiosCode === 'ETIMEDOUT') {
      return new AppError(i18n.global.t('apiErrors.timeout'), undefined, data, true, status)
    }
    if (axiosCode === 'ERR_NETWORK' || !error.response) {
      return new AppError(i18n.global.t('apiErrors.network'), undefined, data, true, status)
    }

    return new AppError(
      error.message || i18n.global.t('apiErrors.requestFailed'),
      undefined,
      data,
      transient,
      status,
    )
  }

  return new AppError(i18n.global.t('apiErrors.requestFailed'))
}
