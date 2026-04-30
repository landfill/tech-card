const RAW_READ_API_BASE = import.meta.env.VITE_API_BASE || ''
const RAW_ADMIN_API_BASE = import.meta.env.VITE_ADMIN_API_BASE || RAW_READ_API_BASE

function trimTrailingSlash(value: string) {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

function joinApi(base: string, path: string) {
  const normalizedBase = trimTrailingSlash(base)
  if (!normalizedBase) return path
  if (normalizedBase.endsWith('/api') && path.startsWith('/api/')) {
    return `${normalizedBase}${path.slice(4)}`
  }
  return `${normalizedBase}${path}`
}

export function readApi(path: string) {
  return joinApi(RAW_READ_API_BASE, path)
}

export function adminApi(path: string) {
  return joinApi(RAW_ADMIN_API_BASE, path)
}
