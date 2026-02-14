import type { MenuRoutersOut } from '@/types/menu'
import { buildFullPath } from '@/router/menu'
import type { Component } from 'vue'

export type AdminResolvedMenu = {
  fullPath: string
  permission: string
  componentPath: string
  name: string
  routeName: string
}

type VueModule = {
  default: Component
}

const viewModules = import.meta.glob<VueModule>('../views/**/*.vue')

const normalizeSlashes = (value: string) => value.replace(/\\/g, '/')

const normalizeComponentPath = (rawPath: string) => {
  const trimmed = normalizeSlashes((rawPath || '').trim()).replace(/[?#].*$/, '')
  if (!trimmed || trimmed === '/') {
    return ''
  }
  const withoutLeading = trimmed.replace(/^\/+/, '')
  if (withoutLeading.startsWith('../views/')) {
    return withoutLeading
  }
  if (withoutLeading.startsWith('@/views/')) {
    return `../views/${withoutLeading.slice('@/views/'.length)}`
  }
  if (withoutLeading.startsWith('src/views/')) {
    return `../views/${withoutLeading.slice('src/views/'.length)}`
  }
  if (withoutLeading.startsWith('views/')) {
    return `../views/${withoutLeading.slice('views/'.length)}`
  }
  return `../views/${withoutLeading}`
}

const buildComponentCandidates = (componentPath: string) => {
  const normalized = normalizeComponentPath(componentPath)
  if (!normalized) {
    return []
  }
  const noExt = normalized.replace(/\.vue$/i, '')
  return [
    normalized.endsWith('.vue') ? normalized : `${normalized}.vue`,
    `${noExt}.vue`,
    `${noExt}/index.vue`,
  ]
}

const resolveMenuByPath = (
  items: MenuRoutersOut[],
  targetPath: string,
  parentPath = '',
  basePath = '/admin',
): AdminResolvedMenu | null => {
  for (const item of items || []) {
    const fullPath = buildFullPath(item, parentPath, basePath)
    if (item.type === 2 && fullPath === targetPath) {
      return {
        fullPath,
        permission: item.permission_char || '',
        componentPath: item.component_path || '',
        name: item.name || '',
        routeName: item.route_name || '',
      }
    }
    if (item.children?.length) {
      const child = resolveMenuByPath(item.children, targetPath, fullPath, basePath)
      if (child) {
        return child
      }
    }
  }
  return null
}

export const findAdminMenuByPath = (
  path: string,
  routers: MenuRoutersOut[],
): AdminResolvedMenu | null => {
  if (!path.startsWith('/admin')) {
    return null
  }
  return resolveMenuByPath(routers, path, '', '/admin')
}

export const resolveAdminViewLoader = (componentPath: string) => {
  const candidates = buildComponentCandidates(componentPath)
  for (const moduleKey of candidates) {
    const loader = viewModules[moduleKey]
    if (loader) {
      return loader
    }
  }
  return null
}
