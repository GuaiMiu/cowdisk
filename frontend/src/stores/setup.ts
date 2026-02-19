import { defineStore } from 'pinia'
import { getSetupStatus } from '@/api/modules/setup'

type SetupState = {
  phase: 'PENDING' | 'RUNNING' | 'FAILED' | 'DONE'
  installed: boolean
  message: string
  updatedAt: string
  checked: boolean
  loading: boolean
}

export const useSetupStore = defineStore('setup', {
  state: (): SetupState => ({
    phase: 'PENDING',
    installed: false,
    message: '',
    updatedAt: '',
    checked: false,
    loading: false,
  }),
  getters: {
    isInstalled: (state) => state.phase === 'DONE' || state.installed,
  },
  actions: {
    async fetchStatus(force = false) {
      if (this.checked && !force) {
        return
      }
      this.loading = true
      try {
        const status = await getSetupStatus()
        this.phase = status?.phase || 'PENDING'
        this.installed = Boolean(status?.installed)
        this.message = status?.message || ''
        this.updatedAt = status?.updated_at || ''
        this.checked = true
      } catch {
        // 状态接口异常时默认允许进入 setup，避免新安装场景被误拦截
        this.phase = 'PENDING'
        this.installed = false
        this.message = ''
        this.updatedAt = ''
        this.checked = true
      } finally {
        this.loading = false
      }
    },
  },
})
