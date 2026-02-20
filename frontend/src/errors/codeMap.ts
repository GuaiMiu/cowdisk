import { i18n } from '@/i18n'

const API_CODE_MESSAGE_KEY: Record<number, string> = {
  100001: 'apiErrors.internal',
  100002: 'apiErrors.badRequest',
  100003: 'apiErrors.conflict',
  100004: 'apiErrors.rateLimited',
  200001: 'apiErrors.unauthorized',
  200002: 'apiErrors.tokenExpired',
  200003: 'apiErrors.tokenInvalid',
  200011: 'apiErrors.invalidCredentials',
  200012: 'apiErrors.accountDisabled',
  200013: 'apiErrors.loginRateLimited',
  200021: 'apiErrors.refreshTokenInvalid',
  200022: 'apiErrors.sessionEnvChanged',
  200023: 'apiErrors.refreshRateLimited',
  300001: 'apiErrors.userNotFound',
  300002: 'apiErrors.conflict',
  300003: 'apiErrors.accountDisabled',
  400001: 'apiErrors.fileNotFound',
  400002: 'apiErrors.badRequest',
  400003: 'apiErrors.badRequest',
  400004: 'apiErrors.badRequest',
  400005: 'apiErrors.badRequest',
  400006: 'apiErrors.badRequest',
  400011: 'apiErrors.nameConflict',
  400012: 'apiErrors.conflict',
  400013: 'apiErrors.conflict',
  400014: 'apiErrors.conflict',
  400015: 'apiErrors.conflict',
  400016: 'apiErrors.conflict',
  400017: 'apiErrors.conflict',
  400021: 'apiErrors.quotaExceeded',
  400022: 'apiErrors.payloadTooLarge',
  400023: 'apiErrors.fileNotFound',
  400024: 'apiErrors.tokenInvalid',
  400025: 'apiErrors.tokenExpired',
  400026: 'apiErrors.badRequest',
  400027: 'apiErrors.badRequest',
  400028: 'apiErrors.internal',
  400029: 'apiErrors.badRequest',
  400030: 'apiErrors.conflict',
  400031: 'apiErrors.uploadSessionNotFound',
  400032: 'apiErrors.chunkIncomplete',
  400033: 'apiErrors.uploadFinalizing',
  400034: 'apiErrors.badRequest',
  400035: 'apiErrors.invalidPartNumber',
  400036: 'apiErrors.badRequest',
  400037: 'apiErrors.badRequest',
  400038: 'apiErrors.conflict',
  400039: 'apiErrors.badRequest',
  500001: 'apiErrors.noPermission',
  500002: 'apiErrors.noPermission',
  600001: 'apiErrors.shareNotFound',
  600011: 'apiErrors.shareExpired',
  600012: 'apiErrors.shareExpired',
  600013: 'apiErrors.shareNotFound',
  600021: 'apiErrors.shareCodeInvalid',
  600022: 'apiErrors.shareCodeRequired',
  600023: 'apiErrors.badRequest',
  600024: 'apiErrors.badRequest',
  600025: 'apiErrors.noPermission',
  700001: 'apiErrors.internal',
  700002: 'apiErrors.tokenInvalid',
  700003: 'apiErrors.tokenExpired',
  700004: 'apiErrors.noPermission',
}

export const resolveCodeMessage = (code?: number) => {
  if (!code) {
    return ''
  }
  const key = API_CODE_MESSAGE_KEY[code]
  if (!key) {
    return ''
  }
  const text = i18n.global.t(key)
  if (!text || text === key) {
    return ''
  }
  return text
}

