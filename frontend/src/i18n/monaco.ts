import { normalizeLocale, type AppLocale } from './utils'

let loadedLocale: AppLocale | null = null

export const loadMonacoLocale = async (locale: string): Promise<AppLocale> => {
  const normalized = normalizeLocale(locale)
  if (loadedLocale === normalized) {
    return normalized
  }
  if (normalized === 'zh-CN') {
    await import('monaco-editor/esm/nls.messages.zh-cn.js')
  } else {
    await import('monaco-editor/esm/nls.messages.js')
  }
  loadedLocale = normalized
  return normalized
}
