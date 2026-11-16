
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    organization_slug: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class OrganizationMembershipResponse(BaseModel):
    organization_id: int
    organization_name: str
    organization_slug: str
    role_code: str
    is_active: bool
    created_at: datetime


class AuthUserResponse(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    organization_id: int
    organization_name: str
    organization_slug: str
    role_code: str
    memberships: list[OrganizationMembershipResponse]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_in: int


class LoginResponse(TokenResponse):
    user: AuthUserResponse
