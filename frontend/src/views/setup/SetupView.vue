<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'
import Switch from '@/components/common/Switch.vue'
import { useMessage } from '@/stores/message'
import { useSetupStore } from '@/stores/setup'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { getSetupDefaults, getSetupProgress, submitSetup } from '@/api/modules/setup'
import type {
  SetupPayload,
  SetupProgressItem,
  SetupResultOut,
} from '@/types/setup'

type ProgressStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'
type RedisAuthMode = 'none' | 'password' | 'username_password'
type ParsedDatabase = {
  type: 'sqlite' | 'mysql'
  sqlitePath: string
  host: string
  port: string
  user: string
  password: string
  name: string
}

const message = useMessage()
const { t } = useI18n({ useScope: 'global' })
const setupStore = useSetupStore()
const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const submitting = ref(false)
const saved = ref(false)
const defaultsLoading = ref(true)
const defaultsReady = ref(false)
const errors = reactive<Record<string, string>>({})
const currentStep = ref(1)
const setupPhase = ref<'form' | 'running' | 'done' | 'failed'>('form')
const setupResult = ref<SetupResultOut | null>(null)
const progressStepsData = ref<Record<string, SetupProgressItem> | null>(null)
const progressTimer = ref<number | null>(null)

const form = reactive({
  appName: '',
  databaseType: 'sqlite',
  databaseHost: '',
  databasePort: '',
  databaseUser: '',
  databasePassword: '',
  databaseName: '',
  sqliteDbPath: '',
  superuserName: '',
  superuserPassword: '',
  superuserMail: '',
  allowRegister: false,
  redisEnable: false,
  redisAuthMode: 'none' as RedisAuthMode,
  redisHost: '',
  redisPort: '',
  redisUsername: '',
  redisPassword: '',
  redisDb: '',
  storagePath: '',
})
const defaultSiteName = computed(() => appStore.siteName || t('setup.brand'))
const setupSteps = [
  { index: 1, title: t('setup.steps.superuser.title'), desc: t('setup.steps.superuser.desc') },
  { index: 2, title: t('setup.steps.system.title'), desc: t('setup.steps.system.desc') },
]
const phaseLabelMap: Record<'form' | 'running' | 'done' | 'failed', string> = {
  form: '',
  running: t('setup.phase.running'),
  done: t('setup.phase.done'),
  failed: t('setup.phase.failed'),
}
const phaseDescriptionMap: Record<'running' | 'done' | 'failed', string> = {
  running: t('setup.phaseDesc.running'),
  done: '',
  failed: t('setup.phaseDesc.failed'),
}
const progressMeta: Record<string, { title: string; detail: string }> = {
  system: { title: t('setup.progress.system.title'), detail: t('setup.progress.system.detail') },
  database: { title: t('setup.progress.database.title'), detail: t('setup.progress.database.detail') },
  superuser: { title: t('setup.progress.superuser.title'), detail: t('setup.progress.superuser.detail') },
  redis: { title: t('setup.progress.redis.title'), detail: t('setup.progress.redis.detail') },
}
const activeStepMeta = computed(() => {
  const matched = setupSteps.find((item) => item.index === currentStep.value)
  return (
    matched || {
      index: 1,
      title: t('setup.steps.superuser.title'),
      desc: t('setup.steps.superuser.desc'),
    }
  )
})

const dbOptions = [
  { label: t('setup.db.sqlite'), value: 'sqlite' },
  { label: t('setup.db.mysql'), value: 'mysql' },
]
const redisAuthModeOptions = [
  { label: t('setup.redis.none'), value: 'none' },
  { label: t('setup.redis.password'), value: 'password' },
  { label: t('setup.redis.userpass'), value: 'username_password' },
]

const isSqlite = computed(() => form.databaseType === 'sqlite')

const buildDatabaseUrl = (): string => {
  if (isSqlite.value) {
    const path = form.sqliteDbPath.trim()
    return path ? `sqlite+aiosqlite:///${path.replace(/\\/g, '/')}` : ''
  }
  const host = form.databaseHost.trim()
  const port = form.databasePort.trim()
  const user = form.databaseUser.trim()
  const password = form.databasePassword
  const name = form.databaseName.trim()
  if (!host || !port || !user || !name) {
    return ''
  }
  return `mysql+aiomysql://${user}:${password}@${host}:${port}/${name}`
}

const parseDatabaseUrl = (databaseUrl: string): ParsedDatabase => {
  const raw = (databaseUrl || '').trim()
  if (raw.startsWith('sqlite+aiosqlite:///')) {
    const sqlitePath = raw.slice('sqlite+aiosqlite:///'.length)
    return {
      type: 'sqlite',
      sqlitePath,
      host: '',
      port: '3306',
      user: '',
      password: '',
      name: '',
    }
  }
  if (raw.startsWith('mysql+aiomysql://')) {
    const body = raw.slice('mysql+aiomysql://'.length)
    const [authAndHost = '', dbName = ''] = body.split('/', 2)
    const [auth = '', hostPort = ''] = authAndHost.split('@', 2)
    const [user = '', password = ''] = auth.split(':', 2)
    const [host = '', port = '3306'] = hostPort.split(':', 2)
    return {
      type: 'mysql',
      sqlitePath: '/app/config/data.db',
      host,
      port: port || '3306',
      user,
      password,
      name: dbName,
    }
  }
  return {
    type: 'sqlite',
    sqlitePath: '/app/config/data.db',
    host: '',
    port: '3306',
    user: '',
    password: '',
    name: '',
  }
}

const clearErrors = () => {
  Object.keys(errors).forEach((key) => {
    errors[key] = ''
  })
}

const validate = () => {
  clearErrors()
  let valid = true
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (currentStep.value === 1) {
    if (!form.superuserName.trim()) {
      errors.superuserName = t('setup.errors.superuserName')
      valid = false
    }
    if (!form.superuserPassword.trim()) {
      errors.superuserPassword = t('setup.errors.superuserPassword')
      valid = false
    }
    if (!form.superuserMail.trim()) {
      errors.superuserMail = t('setup.errors.superuserMail')
      valid = false
    } else if (!emailPattern.test(form.superuserMail.trim())) {
      errors.superuserMail = t('setup.errors.mailFormat')
      valid = false
    }
  }
  if (currentStep.value === 2) {
    if (!form.storagePath.trim()) {
      errors.storagePath = t('setup.errors.storagePath')
      valid = false
    }
    if (!isSqlite.value) {
      if (!form.databaseHost.trim()) {
        errors.databaseHost = t('setup.errors.databaseHost')
        valid = false
      }
      if (!form.databaseUser.trim()) {
        errors.databaseUser = t('setup.errors.databaseUser')
        valid = false
      }
      if (!form.databaseName.trim()) {
        errors.databaseName = t('setup.errors.databaseName')
        valid = false
      }
    } else if (!form.sqliteDbPath.trim()) {
      errors.sqliteDbPath = t('setup.errors.sqliteDbPath')
      valid = false
    }
    const databaseUrl = buildDatabaseUrl()
    if (!databaseUrl) {
      if (isSqlite.value) {
        errors.sqliteDbPath = errors.sqliteDbPath || t('setup.errors.sqliteRequired')
      } else {
        errors.databaseName = errors.databaseName || t('setup.errors.databaseIncomplete')
      }
      valid = false
    }
    if (form.redisEnable) {
      if (!form.redisHost.trim()) {
        errors.redisHost = t('setup.errors.redisHost')
        valid = false
      }
      if (!form.redisPort.trim()) {
        errors.redisPort = t('setup.errors.redisPort')
        valid = false
      }
      if (form.redisAuthMode === 'password' && !form.redisPassword.trim()) {
        errors.redisPassword = t('setup.errors.redisPassword')
        valid = false
      }
      if (form.redisAuthMode === 'username_password') {
        if (!form.redisUsername.trim()) {
          errors.redisUsername = t('setup.errors.redisUsername')
          valid = false
        }
        if (!form.redisPassword.trim()) {
          errors.redisPassword = t('setup.errors.redisPassword')
          valid = false
        }
      }
    }
  }
  return valid
}

const toPayload = (): SetupPayload => ({
  database_url: buildDatabaseUrl(),
  app_name: form.appName.trim() || undefined,
  superuser_name: form.superuserName.trim(),
  superuser_password: form.superuserPassword.trim(),
  superuser_mail: form.superuserMail.trim(),
  allow_register: form.allowRegister,
  redis_enable: form.redisEnable,
  redis_auth_mode: form.redisEnable ? form.redisAuthMode : 'none',
  redis_host: form.redisHost.trim() || undefined,
  redis_port: form.redisPort ? Number(form.redisPort) : undefined,
  redis_username:
    form.redisEnable && form.redisAuthMode === 'username_password'
      ? form.redisUsername.trim() || undefined
      : undefined,
  redis_password:
    form.redisEnable && form.redisAuthMode !== 'none'
      ? form.redisPassword || undefined
      : undefined,
  redis_db: form.redisDb ? Number(form.redisDb) : undefined,
  storage_path: form.storagePath.trim(),
})

const handleSubmit = async () => {
  if (!defaultsReady.value) {
    message.error(t('setup.toast.defaultsTitle'), t('setup.toast.defaultsMessage'))
    return
  }
  if (!validate()) {
    return
  }
  submitting.value = true
  setupPhase.value = 'running'
  setupResult.value = null
  saved.value = false
  progressStepsData.value = null
  startProgressPolling()
  try {
    const result = await submitSetup(toPayload())
    saved.value = true
    setupResult.value = result
    progressStepsData.value = buildProgressFromResult(result)
    setupPhase.value = 'done'
    stopProgressPolling()
    setupStore.phase = 'DONE'
    setupStore.checked = true
    message.success(t('setup.toast.doneTitle'), t('setup.toast.doneMessage'))
  } catch (error) {
    setupPhase.value = 'failed'
    await fetchProgress()
    stopProgressPolling()
    message.error(
      t('setup.toast.saveFailTitle'),
      error instanceof Error ? error.message : t('setup.toast.saveFailMessage'),
    )
  } finally {
    submitting.value = false
  }
}

const handleNext = () => {
  if (!defaultsReady.value) {
    return
  }
  if (!validate()) {
    return
  }
  if (currentStep.value < 2) {
    currentStep.value += 1
  }
}

const handlePrev = () => {
  if (currentStep.value > 1) {
    currentStep.value -= 1
  }
}

const buildProgressFromResult = (result: SetupResultOut): Record<string, SetupProgressItem> => {
  const redisStatus: ProgressStatus = result.redis.skipped
    ? 'skipped'
    : result.redis.ok
    ? 'success'
    : 'failed'
  return {
    system: {
      status: result.system.ok ? 'success' : 'failed',
      message: result.system.message,
    },
    database: {
      status: result.database.ok ? 'success' : 'failed',
      message: result.database.message,
    },
    superuser: {
      status: result.superuser.ok ? 'success' : 'failed',
      message: result.superuser.message,
    },
    redis: {
      status: redisStatus,
      message: result.redis.message,
      skipped: result.redis.skipped,
    },
  }
}

const fetchProgress = async () => {
  try {
    const result = await getSetupProgress()
    progressStepsData.value = result.steps
  } catch {
    // 轮询失败时保留已有进度，避免覆盖掉最后一次有效状态。
  }
}

const startProgressPolling = () => {
  if (progressTimer.value) {
    return
  }
  fetchProgress()
  progressTimer.value = window.setInterval(fetchProgress, 1200)
}

const stopProgressPolling = () => {
  if (progressTimer.value) {
    window.clearInterval(progressTimer.value)
    progressTimer.value = null
  }
}

onUnmounted(() => {
  stopProgressPolling()
})

onMounted(async () => {
  defaultsLoading.value = true
  defaultsReady.value = false
  try {
    const defaults = await getSetupDefaults()
    form.appName = defaults.app_name || form.appName
    const parsedDb = parseDatabaseUrl(defaults.database_url || '')
    form.databaseType = parsedDb.type
    form.sqliteDbPath = parsedDb.sqlitePath
    form.databaseHost = parsedDb.host
    form.databasePort = parsedDb.port
    form.databaseUser = parsedDb.user
    form.databasePassword = parsedDb.password
    form.databaseName = parsedDb.name
    form.superuserName = defaults.superuser_name || form.superuserName
    form.superuserMail = defaults.superuser_mail || form.superuserMail
    form.allowRegister = typeof defaults.allow_register === 'boolean' ? defaults.allow_register : form.allowRegister
    form.redisEnable = typeof defaults.redis_enable === 'boolean' ? defaults.redis_enable : form.redisEnable
    form.redisHost = defaults.redis_host || form.redisHost
    form.redisPort = String(defaults.redis_port ?? form.redisPort)
    form.redisUsername = defaults.redis_username || form.redisUsername
    form.redisAuthMode = defaults.redis_auth_mode || (form.redisUsername ? 'username_password' : 'password')
    form.redisDb = String(defaults.redis_db ?? form.redisDb)
    form.storagePath = defaults.storage_path || form.storagePath
    defaultsReady.value = true
  } catch {
    message.error(t('setup.toast.loadFailTitle'), t('setup.toast.loadFailMessage'))
  } finally {
    defaultsLoading.value = false
  }
})

const progressSteps = computed(() => {
  const statusFallback: ProgressStatus =
    setupPhase.value === 'running'
      ? 'running'
      : setupPhase.value === 'failed'
      ? 'failed'
      : 'pending'
  return Object.entries(progressMeta).map(([key, value]) => {
    const item = progressStepsData.value?.[key]
    const status = (item?.status as ProgressStatus) || statusFallback
    const detail = item?.message || value.detail
    return {
      key,
      title: value.title,
      detail,
      status,
    }
  })
})

const phaseLabel = computed(() => {
  if (setupPhase.value === 'form') {
    return activeStepMeta.value.title
  }
  return phaseLabelMap[setupPhase.value]
})

const phaseDescription = computed(() => {
  if (setupPhase.value === 'form') {
    return activeStepMeta.value.desc
  }
  if (setupPhase.value === 'done') {
    return t('setup.generated', { path: setupResult.value?.env_path || '' })
  }
  return phaseDescriptionMap[setupPhase.value as 'running' | 'failed'] || ''
})

const goLogin = async () => {
  setupStore.phase = 'DONE'
  setupStore.checked = true
  if (authStore.token) {
    await authStore.logout({ silent: true, redirect: false })
  }
  router.replace('/login')
}

const backToForm = () => {
  setupPhase.value = 'form'
}

const getStepState = (index: number) => {
  if (setupPhase.value !== 'form') {
    return 'done'
  }
  if (currentStep.value > index) {
    return 'done'
  }
  if (currentStep.value === index) {
    return 'active'
  }
  return 'pending'
}
</script>

<template>
  <div class="setup-page">
    <div class="setup-shell">
      <aside class="setup-side">
        <div class="side-brand">
          <span class="side-brand__tag">{{ t('setup.sideTag') }}</span>
          <h1>{{ t('setup.title') }}</h1>
          <p>{{ t('setup.subtitle') }}</p>
        </div>

        <ol class="side-steps">
          <li
            v-for="step in setupSteps"
            :key="step.index"
            class="side-step"
            :class="`state-${getStepState(step.index)}`"
          >
            <span class="side-step__index">{{ step.index }}</span>
            <div class="side-step__info">
              <strong>{{ step.title }}</strong>
              <small>{{ step.desc }}</small>
            </div>
          </li>
        </ol>

        <div class="side-hint">
          <h3>{{ t('setup.currentPhase') }}</h3>
          <p>{{ phaseLabel }}</p>
        </div>
      </aside>

      <section class="setup-main">
        <header class="main-head">
          <h2>{{ setupPhase === 'form' ? activeStepMeta.title : t('setup.progressTitle') }}</h2>
          <p v-if="setupPhase !== 'done'">{{ phaseDescription }}</p>
          <p v-else>
            {{ t('setup.generatedLabel') }}：<code>{{ setupResult?.env_path }}</code>
          </p>
        </header>

        <div v-if="setupPhase !== 'form'" class="result-list">
          <article
            v-for="step in progressSteps"
            :key="step.key"
            class="result-item"
            :class="`status-${step.status}`"
          >
            <div class="result-item__bar"></div>
            <div class="result-item__content">
              <h4>{{ step.title }}</h4>
              <p>{{ step.detail }}</p>
            </div>
          </article>

          <footer v-if="setupPhase === 'done'" class="result-actions">
            <Button size="sm" class="setup-action-btn" @click="goLogin">{{ t('setup.goLogin') }}</Button>
          </footer>
          <footer v-else-if="setupPhase === 'failed'" class="result-actions">
            <Button size="sm" class="setup-action-btn" variant="ghost" @click="backToForm">{{ t('setup.backForm') }}</Button>
          </footer>
        </div>

        <form v-else class="setup-form" @submit.prevent="handleSubmit">
          <div v-if="defaultsLoading" class="form-loading">{{ t('setup.loading') }}</div>
          <div v-else-if="!defaultsReady" class="form-loading form-loading--error">
            {{ t('setup.loadFailed') }}
          </div>
          <section v-if="defaultsReady && currentStep === 1" class="form-card">
            <div class="form-card__head">
              <h3>{{ t('setup.steps.superuser.title') }}</h3>
              <p>{{ t('setup.superuserDesc') }}</p>
            </div>
            <div class="form-grid">
              <Input
                v-model="form.superuserName"
                :label="t('setup.superuserName')"
                placeholder="admin"
                :error="errors.superuserName"
              />
              <Input
                v-model="form.superuserPassword"
                :label="t('setup.superuserPassword')"
                type="password"
                :placeholder="t('setup.enterPassword')"
                :error="errors.superuserPassword"
              />
              <Input
                v-model="form.superuserMail"
                :label="t('setup.superuserMail')"
                placeholder="admin@example.com"
                :error="errors.superuserMail"
              />
            </div>
          </section>

        <section v-if="defaultsReady && currentStep === 2" class="form-card">
          <div class="form-card__head">
            <h3>{{ t('setup.systemInfoTitle') }}</h3>
            <p>{{ t('setup.systemInfoDesc') }}</p>
          </div>
          <div class="form-stack">
            <Input v-model="form.appName" :label="t('setup.appName')" :placeholder="defaultSiteName" />
            <div class="toggle-row">
              <div>
                <span>{{ t('setup.allowRegister') }}</span>
                <small>{{ t('setup.allowRegisterDesc') }}</small>
              </div>
              <Switch v-model="form.allowRegister" />
            </div>
            <Input
              v-model="form.storagePath"
              :label="t('setup.storagePath')"
              placeholder="/app/data"
              :error="errors.storagePath"
            />
          </div>
        </section>

        <section v-if="defaultsReady && currentStep === 2" class="form-card">
          <div class="form-card__head">
            <h3>{{ t('setup.databaseCacheTitle') }}</h3>
            <p>{{ t('setup.databaseCacheDesc') }}</p>
          </div>
          <div class="form-stack">
            <Select v-model="form.databaseType" :label="t('setup.databaseType')" :options="dbOptions" />
            <Input
              v-if="isSqlite"
              v-model="form.sqliteDbPath"
              :label="t('setup.sqlitePath')"
              placeholder="/app/config/data.db"
              :error="errors.sqliteDbPath"
            />
            <div v-if="!isSqlite" class="form-grid form-grid--wide">
              <Input
                v-model="form.databaseHost"
                :label="t('setup.databaseHost')"
                placeholder="127.0.0.1"
                :error="errors.databaseHost"
              />
              <Input v-model="form.databasePort" :label="t('setup.port')" placeholder="3306" />
              <Input
                v-model="form.databaseUser"
                :label="t('setup.username')"
                placeholder="backend"
                :error="errors.databaseUser"
              />
              <Input
                v-model="form.databasePassword"
                :label="t('setup.password')"
                type="password"
                placeholder="••••••••"
              />
              <Input
                v-model="form.databaseName"
                :label="t('setup.databaseName')"
                placeholder="backend"
                :error="errors.databaseName"
              />
            </div>
            <div class="toggle-row">
              <div>
                <span>{{ t('setup.redisEnable') }}</span>
                <small>{{ t('setup.redisEnableDesc') }}</small>
              </div>
              <Switch v-model="form.redisEnable" />
            </div>
            <div v-if="form.redisEnable" class="form-grid">
              <Input
                v-model="form.redisHost"
                :label="t('setup.redisHost')"
                placeholder="127.0.0.1"
                :error="errors.redisHost"
              />
              <Input
                v-model="form.redisPort"
                :label="t('setup.port')"
                placeholder="6379"
                :error="errors.redisPort"
              />
              <Select
                v-model="form.redisAuthMode"
                :label="t('setup.redisAuthMode')"
                :options="redisAuthModeOptions"
              />
              <Input
                v-if="form.redisAuthMode === 'username_password'"
                v-model="form.redisUsername"
                :label="t('setup.username')"
                placeholder="default"
                :error="errors.redisUsername"
              />
              <Input
                v-if="form.redisAuthMode !== 'none'"
                v-model="form.redisPassword"
                :label="t('setup.password')"
                type="password"
                :placeholder="t('setup.enterRedisPassword')"
                :error="errors.redisPassword"
              />
              <Input v-model="form.redisDb" label="DB" placeholder="0" />
            </div>
          </div>
        </section>

        <footer class="form-actions">
          <p>{{ t('setup.submitHint') }}</p>
          <div class="form-actions__buttons">
            <Button
              v-if="currentStep > 1"
              class="setup-action-btn"
              size="sm"
              type="button"
              variant="ghost"
              @click="handlePrev"
            >
              {{ t('setup.prevStep') }}
            </Button>
            <Button
              v-if="currentStep < 2"
              class="setup-action-btn"
              size="sm"
              type="button"
              :disabled="!defaultsReady || submitting"
              :loading="submitting"
              @click="handleNext"
            >
              {{ t('setup.nextStep') }}
            </Button>
            <Button
              v-else
              class="setup-action-btn"
              size="sm"
              type="submit"
              :disabled="!defaultsReady || submitting"
              :loading="submitting"
            >
              {{ saved ? t('setup.saved') : t('setup.submit') }}
            </Button>
          </div>
          </footer>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.setup-page {
  height: 100%;
  min-height: 100vh;
  padding: clamp(12px, 2.2vw, 28px);
  display: grid;
  place-items: center;
  overflow-y: auto;
  overflow-x: hidden;
  background:
    radial-gradient(1200px 540px at 8% -14%, color-mix(in srgb, var(--color-primary) 17%, transparent), transparent 62%),
    radial-gradient(900px 460px at 110% 0%, color-mix(in srgb, var(--color-info) 13%, transparent), transparent 64%),
    linear-gradient(160deg, color-mix(in srgb, var(--color-bg) 94%, #fff) 0%, color-mix(in srgb, var(--color-bg) 86%, #f8fafc) 100%);
}

.setup-shell {
  width: min(1180px, 100%);
  min-height: min(820px, calc(100vh - 56px));
  display: grid;
  grid-template-columns: minmax(250px, 320px) 1fr;
  gap: clamp(12px, 1.6vw, 22px);
}

.setup-side,
.setup-main {
  border: 1px solid color-mix(in srgb, var(--color-border) 76%, transparent);
  border-radius: var(--radius-xl);
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-sm);
}

.setup-side {
  padding: clamp(16px, 2vw, 24px);
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: var(--space-4);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--color-surface) 88%, #ffffff) 0%, color-mix(in srgb, var(--color-surface-2) 82%, #fff) 100%);
}

.side-brand {
  display: grid;
  gap: var(--space-2);
}

.side-brand__tag {
  display: inline-flex;
  width: fit-content;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--color-primary) 34%, var(--color-border));
  background: color-mix(in srgb, var(--color-primary) 12%, var(--color-surface));
  color: var(--color-primary);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.side-brand h1 {
  font-size: clamp(26px, 2.7vw, 34px);
  letter-spacing: -0.02em;
  line-height: 1.06;
  color: var(--color-text);
}

.side-brand p {
  font-size: 13px;
  color: var(--color-muted);
  max-width: 24ch;
}

.side-steps {
  display: grid;
  gap: var(--space-2);
}

.side-step {
  display: grid;
  grid-template-columns: 34px 1fr;
  align-items: center;
  gap: var(--space-3);
  padding: 10px;
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--color-border) 82%, transparent);
  background: color-mix(in srgb, var(--color-surface) 74%, transparent);
  transition:
    border-color var(--transition-fast),
    transform var(--transition-fast),
    background var(--transition-fast);
}

.side-step__index {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  border: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-surface) 94%, #fff);
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 700;
}

.side-step__info strong {
  display: block;
  font-size: 13px;
}

.side-step__info small {
  display: block;
  margin-top: 1px;
  font-size: 11px;
  color: var(--color-muted);
}

.side-step.state-active {
  border-color: color-mix(in srgb, var(--color-primary) 64%, var(--color-border));
  background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
  transform: translateX(1px);
}

.side-step.state-active .side-step__index {
  background: linear-gradient(165deg, var(--color-primary) 0%, color-mix(in srgb, var(--color-primary) 72%, #0b5f59) 100%);
  border-color: color-mix(in srgb, var(--color-primary) 80%, #fff);
  color: var(--color-on-primary);
}

.side-step.state-done .side-step__index {
  color: var(--color-success);
  border-color: color-mix(in srgb, var(--color-success) 48%, var(--color-border));
}

.side-hint {
  align-self: end;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px dashed color-mix(in srgb, var(--color-border) 78%, transparent);
  background: color-mix(in srgb, var(--color-surface) 86%, transparent);
}

.side-hint h3 {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.side-hint p {
  margin-top: 7px;
  font-size: 14px;
  font-weight: 600;
}

.setup-main {
  padding: clamp(16px, 2.4vw, 30px);
  display: grid;
  align-content: start;
  gap: var(--space-4);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--color-surface) 94%, #fff) 0%, color-mix(in srgb, var(--color-surface) 90%, #f9fafb) 100%);
}

.main-head {
  display: grid;
  gap: var(--space-2);
}

.main-head h2 {
  font-size: clamp(22px, 2.3vw, 28px);
  line-height: 1.15;
  color: var(--color-text);
}

.main-head p {
  font-size: 13px;
  color: var(--color-muted);
}

.result-list {
  display: grid;
  gap: var(--space-3);
}

.result-item {
  display: grid;
  grid-template-columns: 6px 1fr;
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--color-border) 78%, transparent);
  overflow: hidden;
  background: color-mix(in srgb, var(--color-surface) 88%, transparent);
}

.result-item__bar {
  background: color-mix(in srgb, var(--color-muted) 70%, transparent);
}

.result-item__content {
  padding: 12px 14px;
}

.result-item__content h4 {
  font-size: 14px;
}

.result-item__content p {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-muted);
}

.result-item.status-running .result-item__bar { background: var(--color-info); }
.result-item.status-success .result-item__bar { background: var(--color-success); }
.result-item.status-failed .result-item__bar { background: var(--color-danger); }
.result-item.status-skipped { opacity: 0.74; }

.result-actions {
  margin-top: var(--space-2);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.setup-form {
  display: grid;
  gap: var(--space-4);
}

.form-card {
  padding: clamp(14px, 1.5vw, 18px);
  border-radius: var(--radius-lg);
  border: 1px solid color-mix(in srgb, var(--color-border) 82%, transparent);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--color-surface) 90%, #fff) 0%, color-mix(in srgb, var(--color-surface-2) 82%, #fff) 100%);
  display: grid;
  gap: var(--space-3);
}

.form-card__head {
  display: grid;
  gap: var(--space-1);
}

.form-card__head h3 {
  font-size: 17px;
}

.form-card__head p {
  font-size: 12px;
  color: var(--color-muted);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(188px, 1fr));
  gap: var(--space-3);
}

.form-grid--wide {
  grid-template-columns: repeat(auto-fit, minmax(208px, 1fr));
}

.form-stack {
  display: grid;
  gap: var(--space-3);
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  padding: 11px 12px;
  border: 1px solid color-mix(in srgb, var(--color-border) 84%, transparent);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-surface) 92%, transparent);
}

.toggle-row span {
  display: block;
  font-size: 13px;
  font-weight: 600;
}

.toggle-row small {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--color-muted);
}

.form-actions {
  padding-top: var(--space-3);
  border-top: 1px solid color-mix(in srgb, var(--color-border) 76%, transparent);
  display: grid;
  gap: var(--space-3);
}

.form-actions p {
  font-size: 12px;
  color: var(--color-muted);
}

.form-actions__buttons {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.setup-action-btn {
  width: 120px;
  min-height: 32px;
}

.form-loading {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--color-border) 78%, transparent);
  background: color-mix(in srgb, var(--color-surface) 88%, transparent);
  font-size: 13px;
  color: var(--color-muted);
}

.form-loading--error {
  border-color: color-mix(in srgb, var(--color-danger) 42%, var(--color-border));
  color: var(--color-danger);
}

@media (max-width: 960px) {
  .setup-shell {
    grid-template-columns: 1fr;
    min-height: unset;
  }

  .setup-side {
    grid-template-rows: auto auto;
  }

  .side-hint {
    align-self: auto;
  }
}

@media (max-width: 640px) {
  .setup-page {
    padding: var(--space-3);
    place-items: start center;
  }

  .setup-shell {
    gap: var(--space-3);
  }

  .setup-side,
  .setup-main {
    padding: var(--space-4);
    border-radius: var(--radius-lg);
  }

  .main-head h2 {
    font-size: 22px;
  }

  .setup-action-btn {
    width: 108px;
  }
}
</style>

