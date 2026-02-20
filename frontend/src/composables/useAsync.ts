import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from '@/stores/message'
import { mapToUiError, withErrorCode } from '@/utils/errorMessage'

type AsyncRunOptions = {
  successTitle?: string
  successMessage?: string
  errorTitle?: string
  showSuccess?: boolean
  showError?: boolean
  retryActionLabel?: string
  onRetry?: () => void
}

export const useAsync = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const pending = ref(false)
  const error = ref<unknown>(null)
  const lastResult = ref<unknown>(null)

  const run = async <T>(task: () => Promise<T>, options: AsyncRunOptions = {}) => {
    if (pending.value) {
      return undefined
    }
    pending.value = true
    error.value = null
    try {
      const result = await task()
      lastResult.value = result
      if (options.showSuccess && options.successTitle) {
        message.success(options.successTitle, options.successMessage)
      }
      return result
    } catch (err) {
      error.value = err
      const mapped = mapToUiError(err, options.errorTitle || t('common.operationFailed'))
      if (options.showError !== false) {
        message.error(withErrorCode(mapped.title, mapped.code), mapped.message, {
          action:
            mapped.retryable && options.onRetry
              ? {
                  label: options.retryActionLabel || t('common.retry'),
                  onClick: options.onRetry,
                }
              : undefined,
        })
      }
      return undefined
    } finally {
      pending.value = false
    }
  }

  return {
    pending,
    error,
    lastResult,
    run,
  }
}
