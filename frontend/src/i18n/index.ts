import { createI18n } from 'vue-i18n'
import enUS from './locales/en-US'
import zhCN from './locales/zh-CN'
import { loadMonacoLocale } from './monaco'
import {
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  detectBrowserLocale,
  normalizeLocale,
  type AppLocale,
} from './utils'

const LOCALE_STORAGE_KEY = 'cowdisk-locale'

const messages = {
  'en-US': enUS,
  'zh-CN': zhCN,
} as const

const readStoredLocale = (): string | null => {
  try {
    return localStorage.getItem(LOCALE_STORAGE_KEY)
  } catch {
    return null
  }
}

const persistLocale = (locale: AppLocale) => {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    // Ignore storage errors (private mode, disabled storage).
  }
}

const setDocumentLang = (locale: AppLocale) => {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
  }
}

const initialLocale = normalizeLocale(readStoredLocale() ?? detectBrowserLocale())

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: DEFAULT_LOCALE,
  globalInjection: true,
  messages,
})

export const initI18n = async () => {
  await loadMonacoLocale(initialLocale)
  setDocumentLang(initialLocale)
}

export const setLocale = async (locale: string) => {
  const normalized = normalizeLocale(locale)
  i18n.global.locale.value = normalized
  persistLocale(normalized)
  setDocumentLang(normalized)
  await loadMonacoLocale(normalized)
}

export const getLocale = (): AppLocale =>
  normalizeLocale(i18n.global.locale.value)

export { SUPPORTED_LOCALES, type AppLocale }
