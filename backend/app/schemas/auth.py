from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (excluding sensitive data)."""
    id: int
    email: str
    full_name: Optional[str] = None
    is_verified: bool
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefresh(BaseModel):
    """Schema for refreshing access token."""
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    """Schema for email verification."""
    email: EmailStr
    code: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str


class GoogleOAuthRequest(BaseModel):
    """Schema for Google OAuth login."""
    access_token: str


class GitHubOAuthRequest(BaseModel):
    """Schema for GitHub OAuth login."""
    access_token: str