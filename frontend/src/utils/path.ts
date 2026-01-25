const normalize = (path: string) => path.replace(/\/{2,}/g, '/')

export const joinPath = (base: string, name: string) => {
  if (!base || base === '/') {
    return normalize(`/${name}`)
  }
  return normalize(`${base}/${name}`)
}

export const getSegments = (path: string) => {
  if (!path || path === '/') {
    return []
  }
  return path.split('/').filter(Boolean)
}

export const toRelativePath = (path: string) => {
  if (!path || path === '/') {
    return ''
  }
  return path.replace(/^\/+/, '')
}
