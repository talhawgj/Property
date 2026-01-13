from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class SigninRequest(BaseModel):
    """Request schema for user signin/login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")

class TokenResponse(BaseModel):
    """Response schema for successful authentication"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: "UserResponse" = Field(..., description="Authenticated user information")

class UserResponse(BaseModel):
    """Safe user data response (excludes sensitive information)"""
    id: int
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
