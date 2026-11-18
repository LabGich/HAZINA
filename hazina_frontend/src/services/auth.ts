
import api from './api'
import type {
  AuthUser,
  LoginRequest,
  LoginResponse,
  LogoutRequest,
  RefreshRequest,
  TokenResponse,
} from '../types/auth'

export async function login(
  credentials: LoginRequest,
): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>(
    '/auth/login',
    credentials,
  )

  return response.data
}

export async function refreshTokens(
  payload: RefreshRequest,
): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>(
    '/auth/refresh',
    payload,
  )

  return response.data
}

export async function logout(
  payload: LogoutRequest,
): Promise<void> {
  await api.post('/auth/logout', payload)
}

export async function getCurrentUser(): Promise<AuthUser> {
  const response = await api.get<AuthUser>('/auth/me')

  return response.data
}
