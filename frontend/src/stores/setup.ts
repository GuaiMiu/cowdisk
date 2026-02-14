import { defineStore } from 'pinia'
import { getSetupStatus } from '@/api/modules/setup'

type SetupState = {
  phase: 'PENDING' | 'RUNNING' | 'FAILED' | 'DONE'
  checked: boolean
  loading: boolean
}

export const useSetupStore = defineStore('setup', {
  state: (): SetupState => ({
    phase: 'PENDING',
    checked: false,
    loading: false,
  }),
  getters: {
    installed: (state) => state.phase === 'DONE',
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
        this.checked = true
      } catch {
        // 状态接口异常时默认允许进入 setup，避免新安装场景被误拦截
        this.phase = 'PENDING'
        this.checked = true
      } finally {
        this.loading = false
      }
    },
  },
})
