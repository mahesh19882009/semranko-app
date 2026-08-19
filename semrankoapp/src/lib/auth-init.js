'use client'

import { apiRequest } from './api'
import { store } from '../app/store'

let authInitPromise = null

export async function ensureNotAuthenticated() {
  if (authInitPromise) {
    return authInitPromise
  }

  authInitPromise = apiRequest('/auth/me')
    .then((data) => {
      store.dispatch({ type: 'auth/setUser', payload: data.data || data })
      return { authenticated: true }
    })
    .catch(() => {
      authInitPromise = null
      return { authenticated: false }
    })

  return authInitPromise
}

export function clearAuthInitCache() {
  authInitPromise = null
}
