// tokem mgt module
// responsible for:
// - Holding the access token in memory
// - Persisting the refresh token in sessionStorage
// - Retrieving and clearing tokens
// - Supporting refresh-token rotation
// This keeps token handling separate from API calls

const REFRESH_TOKEN_KEY = 'hazina_refresh_token'

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string): void {
  accessToken = token
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string): void {
  sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
}

export function clearTokens(): void {
  accessToken = null
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}
