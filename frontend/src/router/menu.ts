import type { MenuRoutersOut } from '@/types/menu'

const normalizePath = (path: string) => `/${path}`.replace(/\/{2,}/g, '/').replace(/\/$/, '') || '/'

export const buildFullPath = (node: MenuRoutersOut, parentPath = '', basePath = '') => {
  const normalizedBase = basePath ? normalizePath(basePath) : ''
  const baseSegment = normalizedBase.replace(/^\//, '')
  const segment = node.router_path?.trim() || ''
  if (!segment) {
    return normalizePath(parentPath || normalizedBase || '/')
  }
  if (segment.startsWith('http://') || segment.startsWith('https://')) {
    return segment
  }
  if (baseSegment && segment.startsWith(baseSegment)) {
    return normalizePath(`/${segment}`)
  }
  if (segment.startsWith('/')) {
    if (parentPath && !segment.startsWith(parentPath)) {
      return normalizePath(`${parentPath}${segment}`)
    }
    if (normalizedBase && !segment.startsWith(normalizedBase)) {
      return normalizePath(`${normalizedBase}${segment}`)
    }
    return normalizePath(segment)
  }
  if (!parentPath) {
    if (normalizedBase) {
      return normalizePath(`${normalizedBase}/${segment}`)
    }
    return normalizePath(`/${segment}`)
  }
  return normalizePath(`${parentPath}/${segment}`)
}

const hasPermissionInTree = (node: MenuRoutersOut, permissions: Set<string>): boolean => {
  if (node.permission_char && permissions.has(node.permission_char)) {
    return true
  }
  if (!node.children?.length) {
    return false
  }
  return node.children.some((child) => hasPermissionInTree(child, permissions))
}

const sortMenus = (items: MenuRoutersOut[]): MenuRoutersOut[] =>
  [...items].sort((a, b) => (a.sort ?? 0) - (b.sort ?? 0))

export const filterMenus = (
  items: MenuRoutersOut[],
  permissions: Set<string>,
  isSuperuser = false,
): MenuRoutersOut[] => {
  return sortMenus(items)
    .filter((item) => item.status !== false)
    .filter((item) => item.type !== 3)
    .filter((item) => (isSuperuser ? true : hasPermissionInTree(item, permissions)))
    .map((item) => ({
      ...item,
      children: item.children ? filterMenus(item.children, permissions, isSuperuser) : [],
    }))
}
