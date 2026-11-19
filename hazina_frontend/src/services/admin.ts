
import api from './api'

import type {
  AdminUser,
  AdminCreateUserRequest,
  AdminUpdateMembershipRequest,
} from '../types/admin'

export async function getOrganizationUsers(): Promise<AdminUser[]> {
  const response = await api.get<AdminUser[]>('/admin/users')
  return response.data
}

export async function createOrganizationUser(
  payload: AdminCreateUserRequest,
): Promise<AdminUser> {
  const response = await api.post<AdminUser>(
    '/admin/users',
    payload,
  )

  return response.data
}

export async function updateOrganizationUser(
  userId: number,
  payload: AdminUpdateMembershipRequest,
): Promise<AdminUser> {
  const response = await api.patch<AdminUser>(
    `/admin/users/${userId}`,
    payload,
  )

  return response.data
}

