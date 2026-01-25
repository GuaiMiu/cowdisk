const imageExts = new Set(['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'heic', 'heif'])
const videoExts = new Set(['mp4', 'mov', 'mkv', 'avi', 'flv', 'wmv', 'webm', 'm4v'])
const audioExts = new Set(['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'])
const archiveExts = new Set(['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz'])
const codeExts = new Set([
  'js',
  'ts',
  'jsx',
  'tsx',
  'vue',
  'html',
  'css',
  'scss',
  'less',
  'json',
  'yaml',
  'yml',
  'md',
  'py',
  'go',
  'rb',
  'java',
  'kt',
  'swift',
  'cs',
  'dart',
  'rs',
  'c',
  'cpp',
  'h',
  'hpp',
  'cc',
  'cxx',
  'm',
  'mm',
  'php',
  'sql',
  'sh',
  'bash',
  'zsh',
  'toml',
  'ini',
  'conf',
  'cfg',
  'gradle',
  'properties',
  'make',
  'mk',
  'dockerfile',
])
const docExts = new Set(['doc', 'docx', 'rtf'])
const sheetExts = new Set(['xls', 'xlsx', 'csv'])
const slideExts = new Set(['ppt', 'pptx', 'key'])
const textExts = new Set(['txt', 'log', 'ini', 'conf'])
const pdfExts = new Set(['pdf'])

export type FileKind =
  | 'folder'
  | 'image'
  | 'video'
  | 'audio'
  | 'pdf'
  | 'doc'
  | 'sheet'
  | 'slide'
  | 'archive'
  | 'code'
  | 'text'
  | 'other'

const resolveResourceType = (resourceType?: string) => {
  if (!resourceType) {
    return null
  }
  return resourceType.toLowerCase()
}

const getExtension = (name?: string) => {
  if (!name) {
    return ''
  }
  const cleaned = name.trim()
  const dot = cleaned.lastIndexOf('.')
  if (dot <= 0 || dot === cleaned.length - 1) {
    return ''
  }
  return cleaned.slice(dot + 1).toLowerCase()
}

export const getFileKind = (name?: string, isDir?: boolean, resourceType?: string): FileKind => {
  const normalized = resolveResourceType(resourceType)
  if (isDir || normalized === 'folder' || normalized === 'dir') {
    return 'folder'
  }
  if (normalized === 'file' && !name) {
    return 'other'
  }
  const ext = getExtension(name)
  if (!ext) {
    return 'other'
  }
  if (imageExts.has(ext)) {
    return 'image'
  }
  if (videoExts.has(ext)) {
    return 'video'
  }
  if (audioExts.has(ext)) {
    return 'audio'
  }
  if (pdfExts.has(ext)) {
    return 'pdf'
  }
  if (docExts.has(ext)) {
    return 'doc'
  }
  if (sheetExts.has(ext)) {
    return 'sheet'
  }
  if (slideExts.has(ext)) {
    return 'slide'
  }
  if (archiveExts.has(ext)) {
    return 'archive'
  }
  if (codeExts.has(ext)) {
    return 'code'
  }
  if (textExts.has(ext)) {
    return 'text'
  }
  return 'other'
}
