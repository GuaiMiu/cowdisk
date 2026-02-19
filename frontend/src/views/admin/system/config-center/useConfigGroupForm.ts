import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from '@/stores/message'
import { getConfigGroup, updateConfigGroup } from '@/api/modules/configCenter'
import type { ConfigGroupKey, ConfigSpec } from '@/types/config-center'

const normalizeConfigItems = (payload: unknown): ConfigSpec[] => {
  if (Array.isArray(payload)) {
    return payload as ConfigSpec[]
  }
  if (payload && typeof payload === 'object' && 'items' in payload) {
    const typed = payload as { items?: ConfigSpec[] }
    return typed.items || []
  }
  return []
}

const normalizeFieldValue = (item: ConfigSpec, value: unknown) => {
  if (item.value_type === 'bool') {
    return value === true || value === 'true' || value === 1
  }
  if (item.value_type === 'int') {
    if (value === '' || value === null || value === undefined) {
      return ''
    }
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : ''
  }
  if (item.value_type === 'json') {
    if (value && typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }
    return value ? String(value) : ''
  }
  return value ?? ''
}

const buildRulesHint = (item: ConfigSpec, t: (key: string, named?: Record<string, unknown>) => string) => {
  if (!item.rules) {
    return ''
  }
  const parts: string[] = []
  if (item.rules.min !== undefined || item.rules.max !== undefined) {
    parts.push(t('admin.configShared.rules.range', { min: item.rules.min ?? '-', max: item.rules.max ?? '-' }))
  }
  if (item.rules.min_len !== undefined || item.rules.max_len !== undefined) {
    parts.push(
      t('admin.configShared.rules.length', { min: item.rules.min_len ?? '-', max: item.rules.max_len ?? '-' }),
    )
  }
  if (item.rules.enum?.length) {
    parts.push(t('admin.configShared.rules.enum', { values: item.rules.enum.join(', ') }))
  }
  if (item.rules.regex) {
    parts.push(t('admin.configShared.rules.regex', { regex: item.rules.regex }))
  }
  return parts.join(' · ')
}

const validateItem = (
  item: ConfigSpec,
  rawValue: unknown,
  t: (key: string, named?: Record<string, unknown>) => string,
): string => {
  const rules = item.rules || {}
  if (item.value_type === 'int') {
    const value = typeof rawValue === 'number' ? rawValue : Number(rawValue)
    if (!Number.isInteger(value)) {
      return t('admin.configShared.validation.intRequired')
    }
    if (rules.min !== undefined && value < rules.min) {
      return t('admin.configShared.validation.min', { min: rules.min })
    }
    if (rules.max !== undefined && value > rules.max) {
      return t('admin.configShared.validation.max', { max: rules.max })
    }
  }
  if (item.value_type === 'string') {
    const value = String(rawValue ?? '')
    if (rules.min_len !== undefined && value.length < rules.min_len) {
      return t('admin.configShared.validation.minLen', { min: rules.min_len })
    }
    if (rules.max_len !== undefined && value.length > rules.max_len) {
      return t('admin.configShared.validation.maxLen', { max: rules.max_len })
    }
    if (rules.enum && value && !rules.enum.includes(value)) {
      return t('admin.configShared.validation.enum')
    }
    if (rules.regex) {
      try {
        const reg = new RegExp(rules.regex)
        if (value && !reg.test(value)) {
          return t('admin.configShared.validation.regex')
        }
      } catch {
        return ''
      }
    }
    if ((rules as { url_or_empty?: boolean }).url_or_empty) {
      if (value) {
        try {
          new URL(value)
        } catch {
          return t('admin.configShared.validation.url')
        }
      }
    }
    if ((rules as { timezone?: boolean }).timezone) {
      if (value) {
        try {
          Intl.DateTimeFormat('en-US', { timeZone: value })
        } catch {
          return t('admin.configShared.validation.timezone')
        }
      }
    }
  }
  if (item.value_type === 'json') {
    const value = String(rawValue ?? '')
    if (!value) {
      return ''
    }
    try {
      JSON.parse(value)
    } catch {
      return t('admin.configShared.validation.json')
    }
  }
  return ''
}

const normalizePayloadValue = (item: ConfigSpec, rawValue: unknown) => {
  if (item.value_type === 'bool') {
    return Boolean(rawValue)
  }
  if (item.value_type === 'int') {
    return Number(rawValue)
  }
  if (item.value_type === 'json') {
    return rawValue ? JSON.parse(String(rawValue)) : {}
  }
  return rawValue ?? ''
}

const buildPayload = (items: Array<{ key: string; value: unknown }>) => ({
  items,
})

const createState = () => ({
  items: [] as ConfigSpec[],
  form: {} as Record<string, unknown>,
  errors: {} as Record<string, string>,
  dirtyKeys: new Set<string>(),
  loading: false,
  saving: false,
  editingSecrets: {} as Record<string, boolean>,
})

export const useConfigGroupForm = (group: ConfigGroupKey) => {
  const state = reactive(createState())
  const message = useMessage()
  const { t } = useI18n({ useScope: 'global' })

  const applyItems = (items: ConfigSpec[]) => {
    state.items = items
    state.errors = {}
    state.form = {}
    state.dirtyKeys.clear()
    state.editingSecrets = {}
    items.forEach((item) => {
      state.form[item.key] = normalizeFieldValue(item, item.value ?? item.default)
      if (item.is_secret) {
        state.editingSecrets[item.key] = false
      }
    })
  }

  const load = async () => {
    state.loading = true
    try {
      const payload = await getConfigGroup(group)
      applyItems(normalizeConfigItems(payload))
    } catch (error) {
      message.error(
        t('admin.configShared.toasts.loadFailTitle'),
        error instanceof Error ? error.message : t('admin.configShared.toasts.loadFailMessage'),
      )
    } finally {
      state.loading = false
    }
  }

  const updateValue = (payload: { key: string; value: unknown }) => {
    const target = state.items.find((item) => item.key === payload.key)
    if (target && target.editable === false) {
      return
    }
    state.form[payload.key] = payload.value
    state.dirtyKeys.add(payload.key)
  }

  const enableSecretEdit = (key: string) => {
    state.editingSecrets[key] = true
    state.form[key] = ''
    state.dirtyKeys.add(key)
  }

  const save = async () => {
    state.errors = {}
    const dirtyItems: Array<{ key: string; value: unknown }> = []
    state.items.forEach((item) => {
      if (!state.dirtyKeys.has(item.key)) {
        return
      }
      if (item.editable === false) {
        return
      }
      const value = state.form[item.key]
      const error = validateItem(item, value, t)
      if (error) {
        state.errors[item.key] = error
        return
      }
      dirtyItems.push({ key: item.key, value: normalizePayloadValue(item, value) })
    })
    if (Object.keys(state.errors).length) {
      message.error(t('admin.configShared.toasts.saveFailTitle'), t('admin.configShared.toasts.saveFixErrors'))
      return
    }
    if (!dirtyItems.length) {
      return
    }
    state.saving = true
    try {
      await updateConfigGroup(group, buildPayload(dirtyItems))
      message.success(t('admin.configShared.toasts.saveSuccess'))
    } catch (error) {
      message.error(
        t('admin.configShared.toasts.saveFailTitle'),
        error instanceof Error ? error.message : t('admin.configShared.toasts.saveFailMessage'),
      )
      return
    } finally {
      state.saving = false
    }
    await load()
  }

  return {
    state,
    load,
    save,
    updateValue,
    enableSecretEdit,
    buildRulesHint: (item: ConfigSpec) => buildRulesHint(item, t),
    dirtyCount: () => state.dirtyKeys.size,
  }
}
