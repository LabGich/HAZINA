
export type UserRole = 'ADMIN' | 'OPERATOR' | 'VIEWER'

export interface LoginRequest {
  email: string
  password: string
  organization_slug: string
}

export interface RefreshRequest {
  refresh_token: string
}

export interface LogoutRequest {
  refresh_token: string
}

export interface OrganizationMembership {
  organization_id: number
  organization_name: string
  organization_slug: string
  role_code: UserRole
  is_active: boolean
  created_at: string
}

export interface AuthUser {
  user_id: number
  email: string
  full_name: string
  organization_id: number
  organization_name: string
  organization_slug: string
  role_code: UserRole
  memberships: OrganizationMembership[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  access_token_expires_in: number
}

export interface LoginResponse extends TokenResponse {
  user: AuthUser
}
