function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[2]) : null
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE'])

export async function apiFetch(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { ...options.headers }

  if (!SAFE_METHODS.has(method)) {
    headers['X-CSRFToken'] = getCookie('csrftoken')
  }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const isFullUrl = path.startsWith('/') || path.startsWith('http://') || path.startsWith('https://')
  const url = isFullUrl ? path : `/api/v1/${path}`
  const response = await fetch(url, {
    ...options,
    method,
    headers,
    credentials: 'same-origin',
  })

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error(`API request to ${url} failed with ${response.status}`)
    error.status = response.status
    error.data = data
    throw error
  }
  return data
}
