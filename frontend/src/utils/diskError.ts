import { i18n } from '@/i18n'

export const normalizeDiskError = (error: unknown, fallbackMessage: string) => {
  const t = i18n.global.t
  const message = error instanceof Error ? error.message : ''
  if (!message) {
    return fallbackMessage
  }
  if (message.includes('目录已存在')) {
    return t('fileExplorer.errors.folderExists')
  }
  if (message.includes('文件已存在')) {
    return t('fileExplorer.errors.fileExists')
  }
  if (message.includes('目标已存在')) {
    return t('fileExplorer.errors.targetExists')
  }
  if (message.includes('已在当前目录')) {
    return t('fileExplorer.errors.sameFolder')
  }
  return message
}
