import { computed, ref } from 'vue'
import {
  listDir,
  mkdir,
  renamePath,
  deletePath,
  createDownloadToken,
  getDownloadFileUrl,
  getDownloadJobUrl,
  prepareDownload,
  downloadStatus,
} from '@/api/modules/userDisk'
import { useToastStore } from '@/stores/toast'
import type { DiskEntry } from '@/types/disk'
import { joinPath, toRelativePath } from '@/utils/path'
import { triggerDownload } from '@/utils/download'
import { usePolling } from './usePolling'

export const useDiskExplorer = () => {
  const toast = useToastStore()
  const loading = ref(false)
  const path = ref('/')
  const items = ref<DiskEntry[]>([])
  const { poll } = usePolling()
  const listController = ref<AbortController | null>(null)

  const normalizeRoot = (value: string) => {
    if (!value || value === '/') {
      return ''
    }
    return toRelativePath(value)
  }

  const load = async (nextPath?: string) => {
    loading.value = true
    if (listController.value) {
      listController.value.abort()
    }
    const controller = new AbortController()
    listController.value = controller
    try {
      const target = nextPath ?? path.value
      const data = await listDir(normalizeRoot(target), { signal: controller.signal })
      path.value = data.path || '/'
      items.value = data.items || []
    } catch (error) {
      if (controller.signal.aborted) {
        return
      }
      toast.error('加载失败', error instanceof Error ? error.message : '请稍后重试')
    } finally {
      if (listController.value === controller) {
        listController.value = null
      }
      loading.value = false
    }
  }

  const refresh = () => load(path.value)

  const createFolder = async (name: string) => {
    if (!name.trim()) {
      toast.warning('请输入文件夹名称')
      return false
    }
    try {
      await mkdir({ path: toRelativePath(joinPath(path.value, name.trim())) })
      toast.success('文件夹已创建')
      await refresh()
      return true
    } catch (error) {
      toast.error('创建失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const renameEntry = async (entry: DiskEntry, nextName: string) => {
    if (!nextName.trim()) {
      toast.warning('请输入新名称')
      return false
    }
    try {
      const target = toRelativePath(joinPath(path.value, nextName.trim()))
      await renamePath({ src: entry.path, dst: target, overwrite: false })
      toast.success('重命名成功')
      await refresh()
      return true
    } catch (error) {
      toast.error('重命名失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const moveEntry = async (entry: DiskEntry, targetPath: string) => {
    const base = targetPath ? `/${targetPath}` : '/'
    const target = toRelativePath(joinPath(base, entry.name))
    if (target === entry.path) {
      toast.info('已在当前目录')
      return false
    }
    try {
      await renamePath({ src: entry.path, dst: target, overwrite: false })
      toast.success('移动成功')
      await refresh()
      return true
    } catch (error) {
      toast.error('移动失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const moveEntries = async (entries: DiskEntry[], targetPath: string) => {
    if (!entries.length) {
      toast.warning('未选择文件')
      return false
    }
    const base = targetPath ? `/${targetPath}` : '/'
    let success = 0
    let failed = 0
    for (const entry of entries) {
      const target = toRelativePath(joinPath(base, entry.name))
      if (target === entry.path) {
        failed += 1
        continue
      }
      try {
        await renamePath({ src: entry.path, dst: target, overwrite: false })
        success += 1
      } catch (error) {
        failed += 1
      }
    }
    if (success > 0) {
      toast.success('移动完成', `已移动 ${success} 项`)
      await refresh()
    }
    if (failed > 0) {
      toast.warning('部分移动失败', `失败 ${failed} 项`)
    }
    return success > 0 && failed === 0
  }

  const removeEntry = async (entry: DiskEntry) => {
    try {
      await deletePath(entry.path, entry.is_dir)
      toast.success('已移入回收站')
      await refresh()
      return true
    } catch (error) {
      toast.error('删除失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const downloadEntry = async (entry: DiskEntry) => {
    try {
      if (entry.is_dir) {
        const loadingId = toast.loading('正在打包', '文件夹正在打包，请稍候')
        const job = await prepareDownload({ path: entry.path })
        const status = await poll(
          () => downloadStatus(job.job_id),
          {
            stopCondition: (data) => data.status === 'ready' || data.status === 'error',
            interval: 1500,
          },
        )
        if (status.status !== 'ready') {
          toast.remove(loadingId)
          throw new Error(status.message || '打包失败')
        }
        const token = await createDownloadToken({ job_id: job.job_id })
        triggerDownload(getDownloadJobUrl(token.token))
        toast.remove(loadingId)
        toast.success('打包完成', '已开始下载')
      } else {
        const token = await createDownloadToken({ path: entry.path })
        triggerDownload(getDownloadFileUrl(token.token))
        toast.success('下载已开始')
      }
      return true
    } catch (error) {
      toast.error('下载失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const canGoUp = computed(() => path.value && path.value !== '/')

  return {
    loading,
    path,
    items,
    load,
    refresh,
    createFolder,
    renameEntry,
    moveEntry,
    moveEntries,
    removeEntry,
    downloadEntry,
    canGoUp,
  }
}
