import { computed, type ComputedRef, type Ref } from 'vue'
import type { DiskEntry } from '@/types/disk'
import { getFileKind } from '@/utils/fileType'

export type FileEntryAction =
  | 'download'
  | 'rename'
  | 'delete'
  | 'share'
  | 'detail'
  | 'preview'
  | 'move'
  | 'edit'
  | 'compress'
  | 'extract'

export type FileEntryMenuMode = 'full' | 'more'

export type FileEntryMenuItem = {
  key: string
  label: string
  action: FileEntryAction
  permission?: string
  danger?: boolean
  disabled?: boolean
  dividerBefore?: boolean
}

type Translate = (key: string) => string
type HasPermission = (permission?: string) => boolean

const canEditEntry = (entry: DiskEntry | null) => {
  if (!entry) {
    return false
  }
  if (entry.is_dir) {
    return true
  }
  const kind = getFileKind(entry.name, entry.is_dir)
  return kind === 'text' || kind === 'code' || kind === 'doc' || kind === 'sheet' || kind === 'slide'
}

const canExtractEntry = (entry: DiskEntry | null) => {
  if (!entry || entry.is_dir) {
    return false
  }
  return entry.name.toLowerCase().endsWith('.zip')
}

export const useFileEntryActionsMenu = ({
  entry,
  mode,
  t,
  hasPermission,
}: {
  entry: Ref<DiskEntry | null>
  mode: Ref<FileEntryMenuMode>
  t: Translate
  hasPermission: HasPermission
}): ComputedRef<FileEntryMenuItem[]> =>
  computed(() => {
    const current = entry.value
    if (!current) {
      return []
    }
    const editLabel = current.is_dir ? t('fileTable.actions.openEditor') : t('fileTable.actions.edit')
    const items: FileEntryMenuItem[] = [
      {
        key: 'preview',
        label: t('fileTable.actions.preview'),
        action: 'preview',
        permission: 'disk:file:download',
        disabled: current.is_dir,
      },
      {
        key: 'edit',
        label: editLabel,
        action: 'edit',
        permission: current.is_dir ? 'disk:file:view' : 'disk:file:download',
        disabled: !canEditEntry(current),
      },
    ]

    if (mode.value === 'full') {
      items.push({
        key: 'download',
        label: t('fileTable.actions.download'),
        action: 'download',
        permission: 'disk:file:download',
      })
    }

    items.push({
      key: 'detail',
      label: t('fileTable.actions.details'),
      action: 'detail',
    })
    items.push({
      key: 'compress',
      label: t('fileTable.actions.compress'),
      action: 'compress',
      permission: 'disk:archive:compress',
    })
    items.push({
      key: 'extract',
      label: t('fileTable.actions.extract'),
      action: 'extract',
      permission: 'disk:archive:extract',
      disabled: !canExtractEntry(current),
    })
    items.push(
      {
        key: 'rename',
        label: t('fileTable.actions.rename'),
        action: 'rename',
        permission: 'disk:file:move',
        dividerBefore: true,
      },
      {
        key: 'move',
        label: t('fileTable.actions.move'),
        action: 'move',
        permission: 'disk:file:move',
      },
      {
        key: 'share',
        label: t('fileTable.actions.share'),
        action: 'share',
        permission: 'disk:file:download',
      },
    )

    if (mode.value === 'full') {
      items.push({
        key: 'delete',
        label: t('fileTable.actions.delete'),
        action: 'delete',
        permission: 'disk:file:delete',
        danger: true,
        dividerBefore: true,
      })
    }

    return items.filter((item) => hasPermission(item.permission))
  })
