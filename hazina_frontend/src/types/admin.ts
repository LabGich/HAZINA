
import type { UserRole } from './auth'

export interface AdminUser {
  user_id: number
  email: string
  full_name: string
  user_is_active: boolean
  email_verified: boolean
  membership_id: number
  membership_is_active: boolean
  role_code: UserRole
  membership_created_at: string
}

export interface AdminCreateUserRequest {
  email: string
  password: string
  full_name: string
  role_code: UserRole
}

export interface AdminUpdateMembershipRequest {
  role_code?: UserRole
  is_active?: boolean
}
