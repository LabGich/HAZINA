// Refreshes automatically after an ordinary API request receives HTTP 401
// Uses the latest refresh token
// Saves both newly issued tokens
// Shares one refresh request across simultaneous failed requests
// Retries each original request only once
// Does not recursively intercept login, refresh or logout requests
// Clears tokens and announces session expiration if refresh fails

import axios, {
  type InternalAxiosRequestConfig,
} from 'axios'

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from './tokenStorage'

import type { TokenResponse } from '../types/auth'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

let refreshPromise: Promise<string> | null = null

async function getFreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    const refreshToken = getRefreshToken()

    if (!refreshToken) {
      clearTokens()
      window.dispatchEvent(new Event('hazina:session-expired'))

      throw new Error('No refresh token available')
    }

    refreshPromise = axios
      .post<TokenResponse>(
        '/auth/refresh',
        {
          refresh_token: refreshToken,
        },
        {
          baseURL: API_BASE_URL,
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 30000,
        },
      )
      .then((response) => {
        const tokens = response.data

        setAccessToken(tokens.access_token)
        setRefreshToken(tokens.refresh_token)

        return tokens.access_token
      })
      .catch((error: unknown) => {
        clearTokens()

        window.dispatchEvent(
          new Event('hazina:session-expired'),
        )

        throw error
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

// Attach the current access token to outgoing requests.
api.interceptors.request.use((config) => {
  const token = getAccessToken()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

// Automatically refresh expired access tokens.
api.interceptors.response.use(
  (response) => response,

  async (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return Promise.reject(error)
    }

    const originalRequest = error.config as
      | RetryableRequestConfig
      | undefined

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry
    ) {
      return Promise.reject(error)
    }

    const requestUrl = originalRequest.url ?? ''

    const isAuthEndpoint =
      /\/auth\/(login|refresh|logout)(?:[/?]|$)/.test(requestUrl)

    if (isAuthEndpoint) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      const newAccessToken = await getFreshAccessToken()

      originalRequest.headers.Authorization =
        `Bearer ${newAccessToken}`

      return api(originalRequest)
    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  },
)

export default api
