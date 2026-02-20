import type { AxiosRequestConfig, AxiosResponse } from 'axios'
import { http } from './http'
import { AppError, normalizeError } from './errors'
import type { ResponseModel } from '@/types/response'
import { i18n } from '@/i18n'

type RequestOptions = {
  signal?: AbortSignal
  onUploadProgress?: AxiosRequestConfig['onUploadProgress']
}

const unwrapResponse = <T>(payload: unknown): T => {
  if (payload && typeof payload === 'object' && 'code' in payload) {
    const typed = payload as ResponseModel<T>
    if (typed.code === 100000) {
      return typed.data as T
    }
    throw new AppError(typed.message || i18n.global.t('apiErrors.requestFailed'), typed.code, typed.data)
  }
  return payload as T
}

export const request = async <T>(
  config: AxiosRequestConfig,
  options?: RequestOptions,
): Promise<T> => {
  try {
    const response = await http.request({
      ...config,
      signal: options?.signal,
      onUploadProgress: options?.onUploadProgress,
    })
    return unwrapResponse<T>(response.data)
  } catch (error) {
    throw normalizeError(error)
  }
}

const toFormData = (data?: Record<string, unknown>) => {
  const params = new URLSearchParams()
  if (!data) {
    return params
  }
  Object.entries(data).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return
    }
    params.append(key, String(value))
  })
  return params
}

export const requestForm = async <T>(
  config: AxiosRequestConfig,
  options?: RequestOptions,
): Promise<T> => {
  try {
    const response = await http.request({
      ...config,
      headers: {
        ...(config.headers ?? {}),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      data: toFormData(config.data as Record<string, unknown>),
      signal: options?.signal,
      onUploadProgress: options?.onUploadProgress,
    })
    return unwrapResponse<T>(response.data)
  } catch (error) {
    throw normalizeError(error)
  }
}

const parseFilename = (response: AxiosResponse) => {
  const disposition = response.headers['content-disposition'] as string | undefined
  if (!disposition) {
    return 'download'
  }
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1])
  }
  const asciiMatch = disposition.match(/filename="?([^"]+)"?/i)
  return asciiMatch?.[1] || 'download'
}

export const downloadBlob = async (config: AxiosRequestConfig) => {
  try {
    const response = await http.request({
      ...config,
      responseType: 'blob',
    })
    const contentType = response.headers['content-type'] as string | undefined
    if (contentType && contentType.includes('application/json')) {
      const text = await response.data.text()
      const payload = JSON.parse(text)
      unwrapResponse(payload)
      throw new AppError(i18n.global.t('apiErrors.downloadFailed'))
    }
    return {
      blob: response.data as Blob,
      filename: parseFilename(response),
      contentType: contentType || 'application/octet-stream',
    }
  } catch (error) {
    throw normalizeError(error)
  }
}
