import fetch from 'isomorphic-fetch'
// import cuid from 'cuid'
import * as Cookies from 'js-cookie'

const BASE_URL = '/api'

export const FETCHING = 'api/FETCHING'
export const SUCCESS = 'api/SUCCESS'
export const FAILED = 'api/FAILED'

// action creators
const fetching = request => ({
  type: FETCHING,
  payload: { request },
})
const failed = (request, error) => ({
  type: FAILED,
  payload: { request, error },
})
const success = request => ({
  type: SUCCESS,
  payload: { request },
})

const headBase = {
  method: 'GET',
  credentials: 'same-origin',
  headers: {
    'Content-Type': 'application/json',
  },
}
const csrftoken = Cookies.get('csrftoken')
if (csrftoken) headBase.headers['X-CSRFToken'] = csrftoken

export const apiLogin = ({ username, password }) =>
  apiFetch(
    `${BASE_URL}/rest-auth/login/`,
    { method: 'POST' },
    { username, password }
  )

export const apiLogout = () =>
  apiFetch(`${BASE_URL}/rest-auth/logout/`, { method: 'POST' })

export const apiUser = () =>
  apiFetch(`${BASE_URL}/rest-auth/user/`, { method: 'GET' })

// where the magic happens
export const apiFetch = (url, head = {}, body = null) => {
  const init = R.mergeDeepRight(headBase, { ...head })
  if (body) {
    R.type(body) == 'String'
      ? (init.body = body)
      : (init.body = JSON.stringify(body))
  }
  return fetch(url, init)
    .then(res =>
      res
        .json()
        .then(data => ({ HTTPstatus: res.status, url, ...data }))
        .then(data => (res.ok ? { response: data } : { error: data }))
    )
    .catch(error => ({ error }))
}

export const apiList = (model, attrs = {}) => {
  const query = queryString(attrs)
  const url = query ? `${BASE_URL}/${model}/?${query}` : `${BASE_URL}/${model}/`
  return apiFetch(url)
}

export const apiGet = model => id => {
  return apiFetch(`${BASE_URL}/${model}/${id}/`)
}

export const apiPatch = model => (id, data) => {
  const url = `${BASE_URL}/${model}/${id}/`
  const head = { method: 'PATCH' }
  return apiFetch(url, head, data)
}

export const apiPost = model => data => {
  const url = `${BASE_URL}/${model}/`
  const head = { method: 'POST' }
  return apiFetch(url, head, data)
}

// helpers
const paramPairs = (value, key, _) =>
  value
    ? R.type(value) == 'Array'
        ? `${key}=${value.join(',')}`
        : `${key}=${cleanValues(value)}`
    : null

const cleanValues = R.pipe(String, R.replace(/\s+/g, ' '), encodeURIComponent)

export const queryString = R.pipe(
  R.mapObjIndexed(paramPairs),
  R.values,
  R.filter(Boolean),
  R.join('&')
)

export const searchUrl = model => (attrs = {}) => {
  return `${BASE_URL}/${model}/?${queryString(attrs)}`
}
