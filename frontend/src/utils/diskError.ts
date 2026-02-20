import { i18n } from '@/i18n'
import { normalizeError } from '@/api/errors'

const QUOTA_EXCEEDED_CODE = 400021
const NAME_CONFLICT_CODE = 400011

export const normalizeDiskError = (error: unknown, fallbackMessage: string) => {
  const t = i18n.global.t
  const normalized = normalizeError(error)
  const businessCode = typeof normalized.code === 'number' ? normalized.code : null
  if (businessCode === QUOTA_EXCEEDED_CODE) {
    return t('fileExplorer.errors.quotaExceeded')
  }
  if (businessCode === NAME_CONFLICT_CODE) {
    return t('fileExplorer.errors.targetExists')
  }
  const message = normalized.message
  if (!message) {
    return fallbackMessage
  }
  return message
}
