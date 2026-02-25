export function isMobileLikeDevice(): boolean {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return false
  }

  const ua = (navigator.userAgent || '').toLowerCase()
  const platform = (navigator.platform || '').toLowerCase()
  const touchPoints = Number(navigator.maxTouchPoints || 0)
  const isIpadOsDesktopUa = platform === 'macintel' && touchPoints > 1

  return /android|iphone|ipad|ipod|mobile|windows phone/.test(ua) || isIpadOsDesktopUa
}

