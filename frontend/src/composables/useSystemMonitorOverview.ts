import { ref } from 'vue'
import { getSystemMonitorOverview } from '@/api/modules/adminSystem'
import type { SystemMonitorOverview } from '@/types/system-monitor'

export const useSystemMonitorOverview = () => {
  const loading = ref(false)
  const overview = ref<SystemMonitorOverview | null>(null)

  const load = async () => {
    loading.value = true
    try {
      overview.value = await getSystemMonitorOverview()
      return null
    } catch (error) {
      return error
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    overview,
    load,
  }
}
