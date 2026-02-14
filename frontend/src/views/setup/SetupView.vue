<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
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

const message = useMessage()
const setupStore = useSetupStore()
const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const submitting = ref(false)
const saved = ref(false)
const errors = reactive<Record<string, string>>({})
const currentStep = ref(1)
const setupPhase = ref<'form' | 'running' | 'done'>('form')
const setupResult = ref<SetupResultOut | null>(null)
const progressStepsData = ref<Record<string, SetupProgressItem> | null>(null)
const progressTimer = ref<number | null>(null)

const form = reactive({
  appName: appStore.siteName || 'CowDisk',
  databaseType: 'sqlite',
  databaseHost: '127.0.0.1',
  databasePort: '3306',
  databaseUser: '',
  databasePassword: '',
  databaseName: '',
  databaseUrl: 'sqlite+aiosqlite:///./data.db',
  superuserName: 'admin',
  superuserPassword: '',
  superuserMail: 'admin@example.com',
  allowRegister: true,
  redisEnable: false,
  redisHost: '127.0.0.1',
  redisPort: '6379',
  redisPassword: '',
  redisDb: '0',
  storagePath: '/app/data',
})
const defaultSiteName = computed(() => appStore.siteName || 'CowDisk')
const setupSteps = [
  { index: 1, title: '超级管理员', desc: '创建初始管理员账号' },
  { index: 2, title: '系统信息', desc: '应用名称、存储路径与注册策略' },
  { index: 3, title: '数据库与 Redis', desc: '持久化与缓存连接配置' },
]
const activeStepMeta = computed(() => {
  const matched = setupSteps.find((item) => item.index === currentStep.value)
  return (
    matched || {
      index: 1,
      title: '超级管理员',
      desc: '创建初始管理员账号',
    }
  )
})

const dbOptions = [
  { label: 'SQLite (轻量模式)', value: 'sqlite' },
  { label: 'MySQL (生产推荐)', value: 'mysql' },
]

const isSqlite = computed(() => form.databaseType === 'sqlite')

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
      errors.superuserName = '请输入超级管理员账号'
      valid = false
    }
    if (!form.superuserPassword.trim()) {
      errors.superuserPassword = '请输入超级管理员密码'
      valid = false
    }
    if (!form.superuserMail.trim()) {
      errors.superuserMail = '请输入超级管理员邮箱'
      valid = false
    } else if (!emailPattern.test(form.superuserMail.trim())) {
      errors.superuserMail = '邮箱格式不正确'
      valid = false
    }
  }
  if (currentStep.value === 2) {
    if (!form.storagePath.trim()) {
      errors.storagePath = '请输入文件存储路径'
      valid = false
    }
  }
  if (currentStep.value === 3) {
    if (isSqlite.value) {
      if (!form.databaseUrl.trim()) {
        errors.databaseUrl = '请输入 SQLite 连接地址'
        valid = false
      }
    } else {
      if (!form.databaseHost.trim()) {
        errors.databaseHost = '请输入数据库主机'
        valid = false
      }
      if (!form.databaseUser.trim()) {
        errors.databaseUser = '请输入数据库用户名'
        valid = false
      }
      if (!form.databaseName.trim()) {
        errors.databaseName = '请输入数据库名称'
        valid = false
      }
    }
  }
  return valid
}

const toPayload = (): SetupPayload => ({
  database_type: form.databaseType,
  app_name: form.appName.trim() || undefined,
  database_host: form.databaseHost.trim() || undefined,
  database_port: form.databasePort ? Number(form.databasePort) : undefined,
  database_user: form.databaseUser.trim() || undefined,
  database_password: form.databasePassword || undefined,
  database_name: form.databaseName.trim() || undefined,
  database_url: form.databaseUrl.trim() || undefined,
  superuser_name: form.superuserName.trim(),
  superuser_password: form.superuserPassword.trim(),
  superuser_mail: form.superuserMail.trim(),
  allow_register: form.allowRegister,
  redis_enable: form.redisEnable,
  redis_host: form.redisHost.trim() || undefined,
  redis_port: form.redisPort ? Number(form.redisPort) : undefined,
  redis_password: form.redisPassword || undefined,
  redis_db: form.redisDb ? Number(form.redisDb) : undefined,
  storage_path: form.storagePath.trim(),
})

const handleSubmit = async () => {
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
    message.success('初始化完成', '配置已自动加载')
  } catch (error) {
    setupPhase.value = 'form'
    stopProgressPolling()
    message.error('保存失败', error instanceof Error ? error.message : '请检查配置后重试')
  } finally {
    submitting.value = false
  }
}

const handleNext = () => {
  if (!validate()) {
    return
  }
  if (currentStep.value < 3) {
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
  } catch (error) {
    progressStepsData.value = null
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
  try {
    const defaults = await getSetupDefaults()
    form.appName = defaults.app_name || form.appName
    form.databaseType = defaults.database_type || form.databaseType
    form.databaseHost = defaults.database_host || form.databaseHost
    form.databasePort = String(defaults.database_port ?? form.databasePort)
    form.databaseUser = defaults.database_user || form.databaseUser
    form.databaseName = defaults.database_name || form.databaseName
    form.databaseUrl = defaults.database_url || form.databaseUrl
    form.superuserName = defaults.superuser_name || form.superuserName
    form.superuserMail = defaults.superuser_mail || form.superuserMail
    form.allowRegister = typeof defaults.allow_register === 'boolean' ? defaults.allow_register : form.allowRegister
    form.redisEnable = typeof defaults.redis_enable === 'boolean' ? defaults.redis_enable : form.redisEnable
    form.redisHost = defaults.redis_host || form.redisHost
    form.redisPort = String(defaults.redis_port ?? form.redisPort)
    form.redisDb = String(defaults.redis_db ?? form.redisDb)
    form.storagePath = defaults.storage_path || form.storagePath
  } catch {
    // 默认值接口失败时，保留前端兜底初始值，避免阻断安装页。
  }
})

const progressSteps = computed(() => {
  const meta = {
    system: { title: '系统检查', detail: '检查环境与存储路径' },
    database: { title: '数据库初始化', detail: '初始化数据库表结构' },
    superuser: { title: '管理员创建', detail: '创建初始管理员账号' },
    redis: { title: 'Redis 检查', detail: '验证缓存连接' },
  }
  const statusFallback: ProgressStatus =
    setupPhase.value === 'running' ? 'running' : 'pending'
  return Object.entries(meta).map(([key, value]) => {
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

const goLogin = async () => {
  setupStore.phase = 'DONE'
  setupStore.checked = true
  if (authStore.token) {
    await authStore.logout({ silent: true, redirect: false })
  }
  router.replace('/login')
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
        <span class="side-brand__tag">CowDisk Setup</span>
        <h1>初始化向导</h1>
        <p>仅需三步即可完成管理员、系统与数据服务配置。</p>
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
        <h3>当前阶段</h3>
        <p>{{ setupPhase === 'form' ? activeStepMeta.title : setupPhase === 'running' ? '安装执行中' : '安装完成' }}</p>
      </div>
      </aside>

      <section class="setup-main">
        <header class="main-head">
          <h2>{{ setupPhase === 'form' ? activeStepMeta.title : '安装进度追踪' }}</h2>
          <p v-if="setupPhase === 'form'">{{ activeStepMeta.desc }}</p>
          <p v-else-if="setupPhase === 'running'">正在执行系统检查、数据库初始化与管理员创建。</p>
          <p v-else>配置文件已生成：<code>{{ setupResult?.env_path }}</code></p>
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
            <Button size="sm" @click="goLogin">前往登录</Button>
          </footer>
        </div>

        <form v-else class="setup-form" @submit.prevent="handleSubmit">
          <section v-if="currentStep === 1" class="form-card">
            <div class="form-card__head">
              <h3>超级管理员</h3>
              <p>设置初始化后的首个高权限账号。</p>
            </div>
            <div class="form-grid">
              <Input
                v-model="form.superuserName"
                label="账号"
                placeholder="admin"
                :error="errors.superuserName"
              />
              <Input
                v-model="form.superuserPassword"
                label="密码"
                type="password"
                placeholder="请输入密码"
                :error="errors.superuserPassword"
              />
              <Input
                v-model="form.superuserMail"
                label="邮箱"
                placeholder="admin@example.com"
                :error="errors.superuserMail"
              />
            </div>
          </section>

        <section v-if="currentStep === 2" class="form-card">
          <div class="form-card__head">
            <h3>系统信息</h3>
            <p>设置站点名称、存储目录和注册策略。</p>
          </div>
          <div class="form-stack">
            <Input v-model="form.appName" label="应用名称" :placeholder="defaultSiteName" />
            <div class="toggle-row">
              <div>
                <span>允许注册</span>
                <small>关闭后仅管理员可创建账户</small>
              </div>
              <Switch v-model="form.allowRegister" />
            </div>
            <Input
              v-model="form.storagePath"
              label="文件存储路径"
              placeholder="C:\\data\\cowdisk"
              :error="errors.storagePath"
            />
          </div>
        </section>

        <section v-if="currentStep === 3" class="form-card">
          <div class="form-card__head">
            <h3>数据库与缓存</h3>
            <p>配置持久化数据库以及可选 Redis 缓存服务。</p>
          </div>
          <div class="form-stack">
            <Select v-model="form.databaseType" label="数据库类型" :options="dbOptions" />
            <Input
              v-if="isSqlite"
              v-model="form.databaseUrl"
              label="SQLite 连接"
              placeholder="sqlite+aiosqlite:///./data.db"
              :error="errors.databaseUrl"
            />
            <div v-else class="form-grid form-grid--wide">
              <Input
                v-model="form.databaseHost"
                label="数据库主机"
                placeholder="127.0.0.1"
                :error="errors.databaseHost"
              />
              <Input v-model="form.databasePort" label="端口" placeholder="3306" />
              <Input
                v-model="form.databaseUser"
                label="用户名"
                placeholder="backend"
                :error="errors.databaseUser"
              />
              <Input
                v-model="form.databasePassword"
                label="密码"
                type="password"
                placeholder="••••••••"
              />
              <Input
                v-model="form.databaseName"
                label="数据库名称"
                placeholder="backend"
                :error="errors.databaseName"
              />
            </div>
            <div class="toggle-row">
              <div>
                <span>启用 Redis</span>
                <small>用于提升读写性能和任务调度体验</small>
              </div>
              <Switch v-model="form.redisEnable" />
            </div>
            <div v-if="form.redisEnable" class="form-grid">
              <Input v-model="form.redisHost" label="Redis 主机" placeholder="127.0.0.1" />
              <Input v-model="form.redisPort" label="端口" placeholder="6379" />
              <Input v-model="form.redisPassword" label="密码" type="password" placeholder="可选" />
              <Input v-model="form.redisDb" label="DB" placeholder="0" />
            </div>
          </div>
        </section>

        <footer class="form-actions">
          <p>提交后系统将自动执行初始化，无需手动重启服务。</p>
          <div class="form-actions__buttons">
            <Button
              v-if="currentStep > 1"
              size="sm"
              type="button"
              variant="ghost"
              @click="handlePrev"
            >
              上一步
            </Button>
            <Button
              v-if="currentStep < 3"
              size="sm"
              type="button"
              :loading="submitting"
              @click="handleNext"
            >
              下一步
            </Button>
            <Button v-else size="sm" type="submit" :loading="submitting">
              {{ saved ? '已保存配置' : '生成配置并初始化' }}
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
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: clamp(8px, 1vw, 16px);
}

.setup-shell {
  --accent: #0f766e;
  --accent-soft: color-mix(in srgb, #0f766e 14%, var(--color-panel));
  --ink: #0f172a;
  width: min(1120px, 100%);
  max-width: 1120px;
  margin: 0 auto;
  padding: clamp(10px, 1vw, 16px);
  border-radius: 18px;
  display: grid;
  grid-template-columns: minmax(220px, 300px) 1fr;
  gap: 14px;
}

.setup-side {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--color-border) 82%, transparent);
  background: color-mix(in srgb, var(--color-panel) 94%, #fff);
  display: grid;
  align-content: start;
  gap: 18px;
}

.side-brand__tag {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  background: color-mix(in srgb, #fb923c 16%, transparent);
  color: #9a3412;
  font-size: 11px;
  letter-spacing: 0.05em;
}

.side-brand h1 {
  margin: 10px 0 0;
  color: var(--ink);
  font-size: 30px;
  line-height: 1.1;
}

.side-brand p {
  margin: 10px 0 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.side-steps {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.side-step {
  display: grid;
  grid-template-columns: 30px 1fr;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
  background: color-mix(in srgb, var(--color-surface) 75%, transparent);
}

.side-step__index {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-muted);
  border: 1px solid var(--color-border);
  background: var(--color-panel);
}

.side-step__info strong {
  display: block;
  font-size: 13px;
}

.side-step__info small {
  display: block;
  margin-top: 2px;
  color: var(--color-muted);
  font-size: 11px;
}

.side-step.state-active {
  border-color: color-mix(in srgb, var(--accent) 62%, var(--color-border));
  background: var(--accent-soft);
}

.side-step.state-active .side-step__index {
  color: #fff;
  border-color: var(--accent);
  background: var(--accent);
}

.side-step.state-done .side-step__index {
  color: var(--color-success);
  border-color: color-mix(in srgb, var(--color-success) 50%, var(--color-border));
}

.side-hint {
  padding: 12px;
  border-radius: 12px;
  border: 1px dashed color-mix(in srgb, var(--color-border) 80%, transparent);
}

.side-hint h3 {
  margin: 0;
  font-size: 12px;
  color: var(--color-muted);
}

.side-hint p {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 600;
}

.setup-main {
  padding: 20px;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--color-border) 84%, transparent);
  background: color-mix(in srgb, var(--color-panel) 95%, transparent);
  display: grid;
  gap: 16px;
}

.main-head h2 {
  margin: 0;
  font-size: 24px;
  color: var(--ink);
}

.main-head p {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--color-muted);
}

.result-list {
  display: grid;
  gap: 10px;
}

.result-item {
  display: grid;
  grid-template-columns: 6px 1fr;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.result-item__bar {
  background: var(--color-muted);
}

.result-item__content {
  padding: 12px 14px;
}

.result-item__content h4 {
  margin: 0;
  font-size: 14px;
}

.result-item__content p {
  margin: 5px 0 0;
  font-size: 12px;
  color: var(--color-muted);
}

.result-item.status-running .result-item__bar {
  background: var(--color-info);
}

.result-item.status-success .result-item__bar {
  background: var(--color-success);
}

.result-item.status-failed .result-item__bar {
  background: var(--color-danger);
}

.result-item.status-skipped {
  opacity: 0.75;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
}

.setup-form {
  display: grid;
  gap: 14px;
}

.form-card {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
  background: color-mix(in srgb, var(--color-surface) 72%, transparent);
  display: grid;
  gap: 12px;
}

.form-card__head h3 {
  margin: 0;
  font-size: 16px;
}

.form-card__head p {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--color-muted);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

.form-grid--wide {
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}

.form-stack {
  display: grid;
  gap: 10px;
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-panel);
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
  padding-top: 8px;
  border-top: 1px solid color-mix(in srgb, var(--color-border) 75%, transparent);
  display: grid;
  gap: 10px;
}

.form-actions p {
  margin: 0;
  font-size: 12px;
  color: var(--color-muted);
}

.form-actions__buttons {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.setup-shell :deep(.field) {
  gap: 6px;
}

.setup-shell :deep(.field__label) {
  font-size: 12px;
}

.setup-shell :deep(.input) {
  min-height: 38px;
  padding: 8px 11px;
}

.setup-shell :deep(.field__error) {
  min-height: 14px;
  font-size: 11px;
}

@media (max-width: 900px) {
  .setup-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .setup-shell {
    padding: 8px;
    border-radius: 12px;
  }

  .setup-side,
  .setup-main {
    padding: 14px;
  }
}
</style>
