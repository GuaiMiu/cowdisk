export const SUPPORTED_LOCALES = ['en-US', 'zh-CN'] as const
export type AppLocale = (typeof SUPPORTED_LOCALES)[number]

export const DEFAULT_LOCALE: AppLocale = 'en-US'

export const normalizeLocale = (input?: string): AppLocale => {
  if (!input) {
    return DEFAULT_LOCALE
  }
  const value = input.toLowerCase()
  if (value.startsWith('zh')) {
    return 'zh-CN'
  }
  if (value.startsWith('en')) {
    return 'en-US'
  }
  return DEFAULT_LOCALE
}

export const detectBrowserLocale = (): AppLocale => {
  const candidates =
    typeof navigator === 'undefined'
      ? []
      : navigator.languages?.length
        ? navigator.languages
        : [navigator.language]
  for (const candidate of candidates) {
    const normalized = normalizeLocale(candidate)
    if (SUPPORTED_LOCALES.includes(normalized)) {
      return normalized
    }
  }
  return DEFAULT_LOCALE
}
