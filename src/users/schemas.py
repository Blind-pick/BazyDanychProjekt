"""Users domain schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr = Field(..., description="User email (must be unique and valid)")
    username: str = Field(..., min_length=1, max_length=100, pattern="^[A-Za-z0-9_-]+$", description="Username")


class UserCreate(UserBase):
    """Schema for creating a user."""
    pass


class User(UserBase):
    """Schema for user responses."""
    user_id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
