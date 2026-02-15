const textLanguageMap: Record<string, string> = {
  txt: 'plaintext',
  log: 'plaintext',
  md: 'markdown',
  markdown: 'markdown',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  xml: 'xml',
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'scss',
  less: 'less',
  js: 'javascript',
  ts: 'typescript',
  jsx: 'javascript',
  tsx: 'typescript',
  vue: 'html',
  py: 'python',
  rb: 'ruby',
  go: 'go',
  java: 'java',
  kt: 'kotlin',
  swift: 'swift',
  cs: 'csharp',
  dart: 'dart',
  rs: 'rust',
  c: 'c',
  h: 'c',
  cpp: 'cpp',
  hpp: 'cpp',
  cc: 'cpp',
  cxx: 'cpp',
  m: 'objective-c',
  mm: 'objective-cpp',
  php: 'php',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  sql: 'sql',
  ini: 'ini',
  conf: 'ini',
  cfg: 'ini',
  toml: 'toml',
  gradle: 'groovy',
  properties: 'properties',
  make: 'makefile',
  mk: 'makefile',
}

const videoMimeMap: Record<string, string> = {
  mp4: 'video/mp4',
  webm: 'video/webm',
  mov: 'video/quicktime',
  mkv: 'video/x-matroska',
  avi: 'video/x-msvideo',
  flv: 'video/x-flv',
  wmv: 'video/x-ms-wmv',
  m4v: 'video/x-m4v',
}

const getExtension = (name: string) => name.split('.').pop()?.toLowerCase() || ''

export const getTextLanguage = (name: string) => {
  const ext = getExtension(name)
  return textLanguageMap[ext] || 'plaintext'
}

export const getVideoMime = (name: string) => {
  const ext = getExtension(name)
  return videoMimeMap[ext] || 'video/mp4'
}

