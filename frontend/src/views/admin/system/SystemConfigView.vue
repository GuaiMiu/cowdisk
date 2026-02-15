<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ConfigGroupForm from '@/views/admin/system/config-center/ConfigGroupForm.vue'
import { useConfigGroupForm } from '@/views/admin/system/config-center/useConfigGroupForm'
import Button from '@/components/common/Button.vue'
import { getConfigGroup } from '@/api/modules/configCenter'
import { uploadSiteAsset, type SiteAssetType } from '@/api/modules/setup'
import { request } from '@/api/request'
import { useMessage } from '@/stores/message'
import { useAppStore } from '@/stores/app'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'
import type { ConfigGroupKey, ConfigSpec } from '@/types/config-center'

const systemCfg = useConfigGroupForm('system')
const authCfg = useConfigGroupForm('auth')
const officeCfg = useConfigGroupForm('office')
const storageCfg = useConfigGroupForm('storage')
const uploadCfg = useConfigGroupForm('upload')
const previewCfg = useConfigGroupForm('preview')
const downloadCfg = useConfigGroupForm('download')
const performanceCfg = useConfigGroupForm('performance')
const infraCfg = useConfigGroupForm('infra')
const message = useMessage()
const appStore = useAppStore()
const { t } = useI18n({ useScope: 'global' })
const {
  scrollRef,
  onScroll,
  onMouseEnter,
  onMouseLeave,
  thumbHeight,
  thumbTop,
  visible,
  isScrollable,
  updateMetrics,
  onThumbMouseDown,
} = useOverlayScrollbar()

type TabKey = 'system' | 'auth_access' | 'office' | 'infra' | 'storage_upload' | 'advanced'
const activeTab = ref<TabKey>('system')
const assetInputRefs = {
  logo: ref<HTMLInputElement | null>(null),
  favicon: ref<HTMLInputElement | null>(null),
  login_bg: ref<HTMLInputElement | null>(null),
  theme_image: ref<HTMLInputElement | null>(null),
}
const assetUploading = ref<Record<SiteAssetType, boolean>>({
  logo: false,
  favicon: false,
  login_bg: false,
  theme_image: false,
})
const loaded = {
  system: false,
  auth: false,
  office: false,
  infra: false,
  storage: false,
  upload: false,
  preview: false,
  download: false,
  performance: false,
}

const loadByTab = async (tab: TabKey) => {
  if (tab === 'system' && !loaded.system) {
    await systemCfg.load()
    loaded.system = true
    return
  }
  if (tab === 'auth_access') {
    if (!loaded.auth) {
      await authCfg.load()
      loaded.auth = true
    }
    return
  }
  if (tab === 'infra') {
    if (!loaded.infra) {
      await infraCfg.load()
      loaded.infra = true
    }
    return
  }
  if (tab === 'office') {
    if (!loaded.office) {
      await officeCfg.load()
      loaded.office = true
    }
    return
  }
  if (tab === 'storage_upload') {
    if (!loaded.storage) {
      await storageCfg.load()
      loaded.storage = true
    }
    if (!loaded.upload) {
      await uploadCfg.load()
      loaded.upload = true
    }
    if (!loaded.preview) {
      await previewCfg.load()
      loaded.preview = true
    }
    if (!loaded.download) {
      await downloadCfg.load()
      loaded.download = true
    }
    if (!loaded.performance) {
      await performanceCfg.load()
      loaded.performance = true
    }
  }
}

const advancedLoading = ref(false)
const importText = ref('')
const dryRunReady = ref(false)
const dryRunPreparedCount = ref(0)
const dryRunIssues = ref<Array<{ key: string; error: string }>>([])
let dryRunPreparedItems: Array<{ key: string; value: unknown }> = []
const NON_TRANSFERABLE_GROUPS = new Set<ConfigGroupKey>(['infra'])

const refreshCurrentTab = async () => {
  await loadByTab(activeTab.value)
}

const triggerAssetSelect = (assetType: SiteAssetType) => {
  assetInputRefs[assetType].value?.click()
}

const getAssetPreviewUrl = (assetType: SiteAssetType) => {
  if (assetType === 'logo') {
    return appStore.siteLogoUrl
  }
  if (assetType === 'favicon') {
    return appStore.siteFaviconUrl
  }
  if (assetType === 'login_bg') {
    return appStore.loginBackgroundUrl
  }
  return appStore.themeImageUrl
}

const getAssetLimit = (assetType: SiteAssetType) => (assetType === 'favicon' ? 512 * 1024 : 5 * 1024 * 1024)

const onAssetFileChange = async (assetType: SiteAssetType, event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) {
    return
  }
  if (file.size > getAssetLimit(assetType)) {
    message.error(
      t('admin.systemConfig.branding.uploadFailTitle'),
      t('admin.systemConfig.branding.fileTooLarge'),
    )
    target.value = ''
    return
  }
  assetUploading.value[assetType] = true
  try {
    await uploadSiteAsset(assetType, file)
    await appStore.initRuntimeConfig(true)
    await systemCfg.load()
    message.success(t('admin.systemConfig.branding.uploadSuccess'))
  } catch (error) {
    message.error(
      t('admin.systemConfig.branding.uploadFailTitle'),
      error instanceof Error ? error.message : t('admin.systemConfig.toasts.retryLater'),
    )
  } finally {
    assetUploading.value[assetType] = false
    target.value = ''
  }
}

const exportAllConfig = async () => {
  advancedLoading.value = true
  try {
    const groupsPayload = await request<{ groups: ConfigGroupKey[] }>({
      url: '/api/v1/admin/system/config/groups',
      method: 'GET',
    })
    const groups = (Array.isArray(groupsPayload?.groups) ? groupsPayload.groups : []).filter(
      (group) => !NON_TRANSFERABLE_GROUPS.has(group),
    )
    const output: Record<string, Array<{ key: string; value: unknown }>> = {}
    for (const group of groups) {
      const payload = await getConfigGroup(group)
      const items = Array.isArray(payload) ? payload : payload.items || []
      output[group] = items.map((item: ConfigSpec) => ({ key: item.key, value: item.value }))
    }
    const blob = new Blob(
      [
        JSON.stringify(
          {
            exported_at: new Date().toISOString(),
            groups: output,
          },
          null,
          2,
        ),
      ],
      { type: 'application/json' },
    )
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `config-export-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
    link.click()
    URL.revokeObjectURL(link.href)
    message.success(t('admin.systemConfig.toasts.exportSuccess'))
  } catch (error) {
    message.error(
      t('admin.systemConfig.toasts.exportFailTitle'),
      error instanceof Error ? error.message : t('admin.systemConfig.toasts.retryLater'),
    )
  } finally {
    advancedLoading.value = false
  }
}

const parseImportItems = (parsed: unknown): Array<{ key: string; value: unknown }> => {
  const items: Array<{ key: string; value: unknown }> = []
  if (parsed && typeof parsed === 'object' && 'items' in parsed && Array.isArray(parsed.items)) {
    for (const item of parsed.items) {
      if (item && typeof item === 'object' && 'key' in item) {
        const typed = item as { key: string; value: unknown }
        items.push({ key: typed.key, value: typed.value })
      }
    }
    return items
  }
  if (parsed && typeof parsed === 'object' && 'groups' in parsed && parsed.groups && typeof parsed.groups === 'object') {
    for (const values of Object.values(parsed.groups as Record<string, unknown>)) {
      if (!Array.isArray(values)) {
        continue
      }
      for (const item of values) {
        if (item && typeof item === 'object' && 'key' in item) {
          const typed = item as { key: string; value: unknown }
          items.push({ key: typed.key, value: typed.value })
        }
      }
    }
    return items
  }
  if (parsed && typeof parsed === 'object') {
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      items.push({ key, value })
    }
  }
  return items
}

const validateBySpec = (item: { key: string; value: unknown }, spec: ConfigSpec): string | null => {
  if (spec.editable === false) {
    return t('admin.systemConfig.validation.readonly')
  }
  const value = item.value
  if (spec.value_type === 'int') {
    const num = typeof value === 'number' ? value : Number(value)
    if (!Number.isInteger(num)) {
      return t('admin.systemConfig.validation.intRequired')
    }
    if (spec.rules?.min !== undefined && num < spec.rules.min) {
      return t('admin.systemConfig.validation.min', { min: spec.rules.min })
    }
    if (spec.rules?.max !== undefined && num > spec.rules.max) {
      return t('admin.systemConfig.validation.max', { max: spec.rules.max })
    }
    return null
  }
  if (spec.value_type === 'bool') {
    const ok = typeof value === 'boolean' || ['true', 'false', '1', '0'].includes(String(value))
    return ok ? null : t('admin.systemConfig.validation.boolRequired')
  }
  const text = value === null || value === undefined ? '' : String(value)
  if (spec.rules?.min_len !== undefined && text.length < spec.rules.min_len) {
    return t('admin.systemConfig.validation.minLen', { min: spec.rules.min_len })
  }
  if (spec.rules?.max_len !== undefined && text.length > spec.rules.max_len) {
    return t('admin.systemConfig.validation.maxLen', { max: spec.rules.max_len })
  }
  if (spec.rules?.enum?.length && !spec.rules.enum.includes(text)) {
    return t('admin.systemConfig.validation.enum')
  }
  return null
}

const runDryCheck = async () => {
  if (!importText.value.trim()) {
    message.error(t('admin.systemConfig.toasts.dryRunFailTitle'), t('admin.systemConfig.toasts.pasteJsonFirst'))
    return
  }
  advancedLoading.value = true
  dryRunIssues.value = []
  dryRunPreparedItems = []
  dryRunPreparedCount.value = 0
  dryRunReady.value = false
  try {
    const parsed = JSON.parse(importText.value) as unknown
    const items = parseImportItems(parsed)
    if (!items.length) {
      message.error(t('admin.systemConfig.toasts.dryRunFailTitle'), t('admin.systemConfig.toasts.noImportItems'))
      return
    }

    const groupsPayload = await request<{ groups: ConfigGroupKey[] }>({
      url: '/api/v1/admin/system/config/groups',
      method: 'GET',
    })
    const groups = (Array.isArray(groupsPayload?.groups) ? groupsPayload.groups : []).filter(
      (group) => !NON_TRANSFERABLE_GROUPS.has(group),
    )
    const specMap = new Map<string, ConfigSpec>()
    for (const group of groups) {
      const payload = await getConfigGroup(group)
      const groupItems = Array.isArray(payload) ? payload : payload.items || []
      for (const spec of groupItems) {
        specMap.set(spec.key, spec)
      }
    }

    for (const item of items) {
      const key = String(item.key || '').trim()
      if (!key) {
        dryRunIssues.value.push({ key: '(empty)', error: t('admin.systemConfig.validation.keyRequired') })
        continue
      }
      const spec = specMap.get(key)
      if (!spec) {
        dryRunIssues.value.push({ key, error: t('admin.systemConfig.validation.unknownKey') })
        continue
      }
      const err = validateBySpec(item, spec)
      if (err) {
        dryRunIssues.value.push({ key, error: err })
        continue
      }
      dryRunPreparedItems.push({ key, value: item.value })
    }

    dryRunPreparedCount.value = dryRunPreparedItems.length
    dryRunReady.value = dryRunPreparedItems.length > 0 && dryRunIssues.value.length === 0
    if (dryRunReady.value) {
      message.success(t('admin.systemConfig.toasts.dryRunPass', { count: dryRunPreparedItems.length }))
    } else {
      message.error(
        t('admin.systemConfig.toasts.dryRunNotPassTitle'),
        t('admin.systemConfig.toasts.dryRunNotPassMessage', {
          ok: dryRunPreparedItems.length,
          fail: dryRunIssues.value.length,
        }),
      )
    }
  } catch (error) {
    message.error(
      t('admin.systemConfig.toasts.dryRunFailTitle'),
      error instanceof Error ? error.message : t('admin.systemConfig.validation.invalidJson'),
    )
  } finally {
    advancedLoading.value = false
  }
}

const importConfig = async () => {
  if (!dryRunPreparedItems.length) {
    message.error(t('admin.systemConfig.toasts.importFailTitle'), t('admin.systemConfig.toasts.runDryRunFirst'))
    return
  }
  if (dryRunIssues.value.length > 0) {
    message.error(t('admin.systemConfig.toasts.importFailTitle'), t('admin.systemConfig.toasts.fixDryRunErrors'))
    return
  }
  advancedLoading.value = true
  try {
    await request({
      url: '/api/v1/admin/system/config/batch',
      method: 'PUT',
      data: { items: dryRunPreparedItems },
    })
    message.success(t('admin.systemConfig.toasts.importSuccess', { count: dryRunPreparedItems.length }))
    await refreshCurrentTab()
  } catch (error) {
    message.error(
      t('admin.systemConfig.toasts.importFailTitle'),
      error instanceof Error ? error.message : t('admin.systemConfig.toasts.retryLater'),
    )
  } finally {
    advancedLoading.value = false
  }
}

onMounted(() => {
  void loadByTab(activeTab.value)
})

watch(activeTab, (tab) => {
  void loadByTab(tab)
})

watch(importText, () => {
  dryRunReady.value = false
  dryRunPreparedCount.value = 0
  dryRunIssues.value = []
  dryRunPreparedItems = []
})

watch(
  [
    () => activeTab.value,
    () => systemCfg.state.items.length,
    () => authCfg.state.items.length,
    () => infraCfg.state.items.length,
    () => officeCfg.state.items.length,
    () => storageCfg.state.items.length,
    () => uploadCfg.state.items.length,
    () => previewCfg.state.items.length,
    () => performanceCfg.state.items.length,
    () => downloadCfg.state.items.length,
    () => advancedLoading.value,
    () => dryRunIssues.value.length,
  ],
  async () => {
    await nextTick()
    updateMetrics()
  },
)
</script>

<template>
  <div class="config-page">
    <section class="config-workspace">
      <div class="tabs" role="tablist" :aria-label="t('admin.systemConfig.tabs.aria')">
        <button
          type="button"
          class="tab"
          :class="{ 'tab--active': activeTab === 'system' }"
          @click="activeTab = 'system'"
        >
          {{ t('admin.systemConfig.tabs.system') }}
        </button>
        <button
          type="button"
          class="tab"
          :class="{ 'tab--active': activeTab === 'auth_access' }"
          @click="activeTab = 'auth_access'"
        >
          {{ t('admin.systemConfig.tabs.authAccess') }}
        </button>
        <button
          type="button"
          class="tab"
          :class="{ 'tab--active': activeTab === 'office' }"
          @click="activeTab = 'office'"
        >
          {{ t('admin.systemConfig.tabs.office') }}
        </button>
        <button
          type="button"
          class="tab"
          :class="{ 'tab--active': activeTab === 'infra' }"
          @click="activeTab = 'infra'"
        >
          {{ t('admin.systemConfig.tabs.infra') }}
        </button>
        <button
          type="button"
          class="tab"
          :class="{ 'tab--active': activeTab === 'storage_upload' }"
          @click="activeTab = 'storage_upload'"
        >
          {{ t('admin.systemConfig.tabs.storageUpload') }}
        </button>
        <button
          type="button"
          class="tab"
          :class="{ 'tab--active': activeTab === 'advanced' }"
          @click="activeTab = 'advanced'"
        >
          {{ t('admin.systemConfig.tabs.advanced') }}
        </button>
      </div>

      <div class="tab-content" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
        <div ref="scrollRef" class="tab-content__scroll overlay-scroll" @scroll="onScroll">
          <template v-if="activeTab === 'system'">
          <section class="branding-panel">
            <header class="branding-panel__header">
              <h3>{{ t('admin.systemConfig.branding.title') }}</h3>
              <p>{{ t('admin.systemConfig.branding.desc') }}</p>
            </header>
            <div class="branding-grid">
              <article class="branding-item">
                <div class="branding-item__preview">
                  <img v-if="getAssetPreviewUrl('logo')" :src="getAssetPreviewUrl('logo')" alt="logo" class="branding-item__image" />
                  <div v-else class="branding-item__placeholder">{{ t('admin.systemConfig.branding.notSet') }}</div>
                </div>
                <div class="branding-item__meta">
                  <h4>{{ t('admin.systemConfig.branding.logoTitle') }}</h4>
                  <p>{{ t('admin.systemConfig.branding.logoHint') }}</p>
                  <input
                    :ref="assetInputRefs.logo"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/svg+xml"
                    class="branding-item__input"
                    @change="(e) => onAssetFileChange('logo', e)"
                  />
                  <Button variant="secondary" :loading="assetUploading.logo" @click="triggerAssetSelect('logo')">
                    {{ t('admin.systemConfig.branding.uploadButton') }}
                  </Button>
                </div>
              </article>

              <article class="branding-item">
                <div class="branding-item__preview branding-item__preview--small">
                  <img
                    v-if="getAssetPreviewUrl('favicon')"
                    :src="getAssetPreviewUrl('favicon')"
                    alt="favicon"
                    class="branding-item__image branding-item__image--icon"
                  />
                  <div v-else class="branding-item__placeholder">{{ t('admin.systemConfig.branding.notSet') }}</div>
                </div>
                <div class="branding-item__meta">
                  <h4>{{ t('admin.systemConfig.branding.faviconTitle') }}</h4>
                  <p>{{ t('admin.systemConfig.branding.faviconHint') }}</p>
                  <input
                    :ref="assetInputRefs.favicon"
                    type="file"
                    accept="image/png,image/x-icon,image/vnd.microsoft.icon,image/svg+xml"
                    class="branding-item__input"
                    @change="(e) => onAssetFileChange('favicon', e)"
                  />
                  <Button variant="secondary" :loading="assetUploading.favicon" @click="triggerAssetSelect('favicon')">
                    {{ t('admin.systemConfig.branding.uploadButton') }}
                  </Button>
                </div>
              </article>

              <article class="branding-item">
                <div class="branding-item__preview branding-item__preview--wide">
                  <img v-if="getAssetPreviewUrl('login_bg')" :src="getAssetPreviewUrl('login_bg')" alt="login-background" class="branding-item__image" />
                  <div v-else class="branding-item__placeholder">{{ t('admin.systemConfig.branding.notSet') }}</div>
                </div>
                <div class="branding-item__meta">
                  <h4>{{ t('admin.systemConfig.branding.loginBgTitle') }}</h4>
                  <p>{{ t('admin.systemConfig.branding.loginBgHint') }}</p>
                  <input
                    :ref="assetInputRefs.login_bg"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    class="branding-item__input"
                    @change="(e) => onAssetFileChange('login_bg', e)"
                  />
                  <Button variant="secondary" :loading="assetUploading.login_bg" @click="triggerAssetSelect('login_bg')">
                    {{ t('admin.systemConfig.branding.uploadButton') }}
                  </Button>
                </div>
              </article>

              <article class="branding-item">
                <div class="branding-item__preview branding-item__preview--wide">
                  <img v-if="getAssetPreviewUrl('theme_image')" :src="getAssetPreviewUrl('theme_image')" alt="theme-image" class="branding-item__image" />
                  <div v-else class="branding-item__placeholder">{{ t('admin.systemConfig.branding.notSet') }}</div>
                </div>
                <div class="branding-item__meta">
                  <h4>{{ t('admin.systemConfig.branding.themeImageTitle') }}</h4>
                  <p>{{ t('admin.systemConfig.branding.themeImageHint') }}</p>
                  <input
                    :ref="assetInputRefs.theme_image"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/svg+xml"
                    class="branding-item__input"
                    @change="(e) => onAssetFileChange('theme_image', e)"
                  />
                  <Button variant="secondary" :loading="assetUploading.theme_image" @click="triggerAssetSelect('theme_image')">
                    {{ t('admin.systemConfig.branding.uploadButton') }}
                  </Button>
                </div>
              </article>
            </div>
          </section>
          <ConfigGroupForm
            :panel-title="t('admin.systemConfig.panels.system.title')"
            :panel-subtitle="t('admin.systemConfig.panels.system.subtitle')"
            :items="systemCfg.state.items"
            :form="systemCfg.state.form"
            :errors="systemCfg.state.errors"
            :editing-secrets="systemCfg.state.editingSecrets"
            :loading="systemCfg.state.loading"
            :saving="systemCfg.state.saving"
            :dirty-count="systemCfg.dirtyCount()"
            :build-rules-hint="systemCfg.buildRulesHint"
            :save-label="t('admin.systemConfig.panels.system.save')"
            @save="systemCfg.save"
            @edit-secret="systemCfg.enableSecretEdit"
            @update="systemCfg.updateValue"
          />
          </template>

          <template v-else-if="activeTab === 'auth_access'">
          <div class="single-panel-wrap">
            <ConfigGroupForm
              :panel-title="t('admin.systemConfig.panels.auth.title')"
              :panel-subtitle="t('admin.systemConfig.panels.auth.subtitle')"
              :items="authCfg.state.items"
              :form="authCfg.state.form"
              :errors="authCfg.state.errors"
              :editing-secrets="authCfg.state.editingSecrets"
              :loading="authCfg.state.loading"
              :saving="authCfg.state.saving"
              :dirty-count="authCfg.dirtyCount()"
              :build-rules-hint="authCfg.buildRulesHint"
              :save-label="t('admin.systemConfig.panels.auth.save')"
              @save="authCfg.save"
              @edit-secret="authCfg.enableSecretEdit"
              @update="authCfg.updateValue"
            />
          </div>
          </template>

          <template v-else-if="activeTab === 'infra'">
          <div class="single-panel-wrap">
            <ConfigGroupForm
              :panel-title="t('admin.systemConfig.panels.infra.title')"
              :panel-subtitle="t('admin.systemConfig.panels.infra.subtitle')"
              :items="infraCfg.state.items"
              :form="infraCfg.state.form"
              :errors="infraCfg.state.errors"
              :editing-secrets="infraCfg.state.editingSecrets"
              :loading="infraCfg.state.loading"
              :saving="infraCfg.state.saving"
              :dirty-count="infraCfg.dirtyCount()"
              :build-rules-hint="infraCfg.buildRulesHint"
              :save-label="t('admin.systemConfig.panels.infra.save')"
              @save="infraCfg.save"
              @edit-secret="infraCfg.enableSecretEdit"
              @update="infraCfg.updateValue"
            />
          </div>
          </template>

          <template v-else-if="activeTab === 'office'">
          <div class="single-panel-wrap">
            <ConfigGroupForm
              :panel-title="t('admin.systemConfig.panels.office.title')"
              :panel-subtitle="t('admin.systemConfig.panels.office.subtitle')"
              :items="officeCfg.state.items"
              :form="officeCfg.state.form"
              :errors="officeCfg.state.errors"
              :editing-secrets="officeCfg.state.editingSecrets"
              :loading="officeCfg.state.loading"
              :saving="officeCfg.state.saving"
              :dirty-count="officeCfg.dirtyCount()"
              :build-rules-hint="officeCfg.buildRulesHint"
              :save-label="t('admin.systemConfig.panels.office.save')"
              @save="officeCfg.save"
              @edit-secret="officeCfg.enableSecretEdit"
              @update="officeCfg.updateValue"
            />
          </div>
          </template>

          <template v-else-if="activeTab === 'storage_upload'">
          <ConfigGroupForm
            :panel-title="t('admin.systemConfig.panels.storage.title')"
            :panel-subtitle="t('admin.systemConfig.panels.storage.subtitle')"
            :items="storageCfg.state.items"
            :form="storageCfg.state.form"
            :errors="storageCfg.state.errors"
            :editing-secrets="storageCfg.state.editingSecrets"
            :loading="storageCfg.state.loading"
            :saving="storageCfg.state.saving"
            :dirty-count="storageCfg.dirtyCount()"
            :build-rules-hint="storageCfg.buildRulesHint"
            :save-label="t('admin.systemConfig.panels.storage.save')"
            @save="storageCfg.save"
            @edit-secret="storageCfg.enableSecretEdit"
            @update="storageCfg.updateValue"
          />
          <ConfigGroupForm
            :panel-title="t('admin.systemConfig.panels.upload.title')"
            :panel-subtitle="t('admin.systemConfig.panels.upload.subtitle')"
            :items="uploadCfg.state.items"
            :form="uploadCfg.state.form"
            :errors="uploadCfg.state.errors"
            :editing-secrets="uploadCfg.state.editingSecrets"
            :loading="uploadCfg.state.loading"
            :saving="uploadCfg.state.saving"
            :dirty-count="uploadCfg.dirtyCount()"
            :build-rules-hint="uploadCfg.buildRulesHint"
            :save-label="t('admin.systemConfig.panels.upload.save')"
            @save="uploadCfg.save"
            @edit-secret="uploadCfg.enableSecretEdit"
            @update="uploadCfg.updateValue"
          />
          <ConfigGroupForm
            :panel-title="t('admin.systemConfig.panels.preview.title')"
            :panel-subtitle="t('admin.systemConfig.panels.preview.subtitle')"
            :items="previewCfg.state.items"
            :form="previewCfg.state.form"
            :errors="previewCfg.state.errors"
            :editing-secrets="previewCfg.state.editingSecrets"
            :loading="previewCfg.state.loading"
            :saving="previewCfg.state.saving"
            :dirty-count="previewCfg.dirtyCount()"
            :build-rules-hint="previewCfg.buildRulesHint"
            :save-label="t('admin.systemConfig.panels.preview.save')"
            @save="previewCfg.save"
            @edit-secret="previewCfg.enableSecretEdit"
            @update="previewCfg.updateValue"
          />
          <ConfigGroupForm
            :panel-title="t('admin.systemConfig.panels.performance.title')"
            :panel-subtitle="t('admin.systemConfig.panels.performance.subtitle')"
            :items="performanceCfg.state.items"
            :form="performanceCfg.state.form"
            :errors="performanceCfg.state.errors"
            :editing-secrets="performanceCfg.state.editingSecrets"
            :loading="performanceCfg.state.loading"
            :saving="performanceCfg.state.saving"
            :dirty-count="performanceCfg.dirtyCount()"
            :build-rules-hint="performanceCfg.buildRulesHint"
            :save-label="t('admin.systemConfig.panels.performance.save')"
            @save="performanceCfg.save"
            @edit-secret="performanceCfg.enableSecretEdit"
            @update="performanceCfg.updateValue"
          />
          <ConfigGroupForm
            :panel-title="t('admin.systemConfig.panels.download.title')"
            :panel-subtitle="t('admin.systemConfig.panels.download.subtitle')"
            :items="downloadCfg.state.items"
            :form="downloadCfg.state.form"
            :errors="downloadCfg.state.errors"
            :editing-secrets="downloadCfg.state.editingSecrets"
            :loading="downloadCfg.state.loading"
            :saving="downloadCfg.state.saving"
            :dirty-count="downloadCfg.dirtyCount()"
            :build-rules-hint="downloadCfg.buildRulesHint"
            :save-label="t('admin.systemConfig.panels.download.save')"
            @save="downloadCfg.save"
            @edit-secret="downloadCfg.enableSecretEdit"
            @update="downloadCfg.updateValue"
          />
          </template>

          <template v-else>
          <div class="advanced-tools">
            <div class="tool-card">
              <h3>{{ t('admin.systemConfig.advanced.exportTitle') }}</h3>
              <p>{{ t('admin.systemConfig.advanced.exportDesc') }}</p>
              <Button variant="secondary" :loading="advancedLoading" @click="exportAllConfig">
                {{ t('admin.systemConfig.advanced.exportBtn') }}
              </Button>
            </div>
            <div class="tool-card">
              <h3>{{ t('admin.systemConfig.advanced.importTitle') }}</h3>
              <p>{{ t('admin.systemConfig.advanced.importDesc') }}</p>
              <textarea
                v-model="importText"
                class="json-input"
                rows="14"
                :placeholder="t('admin.systemConfig.advanced.importPlaceholder')"
              />
              <div class="tool-actions">
                <Button variant="secondary" :loading="advancedLoading" @click="refreshCurrentTab">
                  {{ t('admin.systemConfig.advanced.refreshTab') }}
                </Button>
                <Button variant="secondary" :loading="advancedLoading" @click="runDryCheck">
                  {{ t('admin.systemConfig.advanced.dryRun') }}
                </Button>
                <Button
                  variant="primary"
                  :loading="advancedLoading"
                  :disabled="!dryRunReady"
                  @click="importConfig"
                >
                  {{ t('admin.systemConfig.advanced.importBtn') }}
                </Button>
              </div>
              <div class="dry-run-result">
                <div class="dry-run-summary">
                  <span>{{ t('admin.systemConfig.advanced.readyCount', { count: dryRunPreparedCount }) }}</span>
                  <span>{{ t('admin.systemConfig.advanced.errorCount', { count: dryRunIssues.length }) }}</span>
                </div>
                <ul v-if="dryRunIssues.length" class="dry-run-errors">
                  <li v-for="issue in dryRunIssues" :key="`${issue.key}-${issue.error}`">
                    <code>{{ issue.key }}</code> - {{ issue.error }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
          </template>
        </div>
        <div v-if="isScrollable" class="overlay-scrollbar" :class="{ 'is-visible': visible }">
          <div
            class="overlay-scrollbar__thumb"
            :style="{ height: `${thumbHeight}px`, transform: `translateY(${thumbTop}px)` }"
            @mousedown="onThumbMouseDown"
          ></div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.config-page {
  display: grid;
  gap: var(--space-4);
  height: 100%;
  min-height: 0;
  align-content: stretch;
  overflow: hidden;
}

.config-workspace {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 0;
  min-height: 0;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: 8px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.tab {
  border: 1px solid transparent;
  background: color-mix(in srgb, var(--color-surface-2) 45%, transparent);
  color: var(--color-muted);
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 500;
  transition:
    color var(--transition-base),
    border-color var(--transition-base),
    background var(--transition-base);
}

.tab--active {
  color: var(--color-primary);
  border-color: color-mix(in srgb, var(--color-primary) 30%, var(--color-border));
  background: color-mix(in srgb, var(--color-primary) 12%, var(--color-surface));
}

.tab-content {
  position: relative;
  border: 1px solid var(--color-border);
  border-top: 0;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  overflow: hidden;
  background: color-mix(in srgb, var(--color-surface-2) 28%, var(--color-surface));
  min-height: 0;
}

.tab-content__scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: var(--space-4);
  align-content: start;
  padding: var(--space-4);
}

.single-panel-wrap {
  width: 100%;
}

.advanced-tools {
  display: grid;
  gap: var(--space-6);
}

.branding-panel {
  display: grid;
  gap: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.branding-panel__header h3,
.branding-panel__header p {
  margin: 0;
}

.branding-panel__header p {
  color: var(--color-muted);
}

.branding-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: var(--space-4);
}

.branding-item {
  display: grid;
  grid-template-columns: minmax(96px, 140px) minmax(0, 1fr);
  gap: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  background: color-mix(in srgb, var(--color-surface-2) 30%, var(--color-surface));
  align-items: center;
}

.branding-item__preview {
  --preview-w: 140px;
  --preview-h: 104px;
  width: min(100%, var(--preview-w));
  height: var(--preview-h);
  border-radius: var(--radius-sm);
  border: 1px dashed var(--color-border);
  background: var(--color-surface);
  display: grid;
  place-items: center;
  overflow: hidden;
  justify-self: center;
}

.branding-item__preview--small {
  --preview-w: 72px;
  --preview-h: 72px;
}

.branding-item__preview--wide {
  --preview-w: 140px;
  --preview-h: 88px;
}

.branding-item__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  display: block;
}

.branding-item__image--icon {
  width: 68%;
  height: 68%;
  object-fit: contain;
}

.branding-item__placeholder {
  font-size: 12px;
  color: var(--color-muted);
  text-align: center;
  padding: 0 var(--space-2);
}

.branding-item__meta {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.branding-item__meta p {
  color: var(--color-muted);
  font-size: 12px;
  margin: 0;
}

.branding-item__input {
  display: none;
}

@media (max-width: 840px) {
  .branding-item {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .branding-item__preview {
    justify-self: start;
  }
}

.tool-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  display: grid;
  gap: var(--space-3);
}

.tool-card p {
  color: var(--color-muted);
}

.json-input {
  width: 100%;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  padding: var(--space-3);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  resize: vertical;
  min-height: 240px;
}

.tool-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.dry-run-result {
  border-top: 1px dashed var(--color-border);
  padding-top: var(--space-3);
  display: grid;
  gap: var(--space-2);
}

.dry-run-summary {
  display: flex;
  gap: var(--space-4);
  color: var(--color-muted);
  font-size: 13px;
}

.dry-run-errors {
  margin: 0;
  padding-left: 18px;
  color: var(--color-danger);
  font-size: 13px;
  display: grid;
  gap: 4px;
  max-height: 180px;
  overflow: auto;
}
</style>
