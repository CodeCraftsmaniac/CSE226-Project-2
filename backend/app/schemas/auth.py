"""
Authentication Schemas
======================
Shared Pydantic models for authentication responses.
NOTE: Endpoint-specific request/response models are defined inline in
app.api.v1.auth to keep them co-located with their handlers.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class AuthTokenResponse(BaseModel):
    """Authentication token response (schema-level definition)."""
    success: bool = True
    message: Optional[str] = None
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")

    class Config:
        from_attributes = True


class AuthUserInfo(BaseModel):
    """User information response (schema-level definition)."""
    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    name: Optional[str] = Field(None, description="Display name")
    email_verified: bool = Field(False, description="Email verification status")
    created_at: Optional[datetime] = Field(None, description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")

    class Config:
        from_attributes = True
