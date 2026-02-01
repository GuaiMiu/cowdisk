export const formatBytes = (bytes: number) => {
  if (!Number.isFinite(bytes)) {
    return '-'
  }
  if (bytes === 0) {
    return '0 B'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / Math.pow(1024, index)
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

export const formatTime = (value?: string | number | null) => {
  if (value === undefined || value === null) {
    return '-'
  }
  const normalized = typeof value === 'number' ? value : /^\d+$/.test(value) ? Number(value) : value
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }
  const y = date.getFullYear()
  const m = `${date.getMonth() + 1}`.padStart(2, '0')
  const d = `${date.getDate()}`.padStart(2, '0')
  const hh = `${date.getHours()}`.padStart(2, '0')
  const mm = `${date.getMinutes()}`.padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}
