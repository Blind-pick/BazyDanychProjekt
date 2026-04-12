"""Cinemas domain schemas (Pydantic models)."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CinemaBase(BaseModel):
    """Base schema for cinema data."""
    name: str = Field(..., min_length=1, max_length=255, description="Cinema name")
    city: str = Field(..., min_length=1, max_length=255, description="City location")


class CinemaCreate(CinemaBase):
    """Schema for creating a cinema."""
    pass


class Cinema(CinemaBase):
    """Schema for cinema responses."""
    cinema_id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CinemaList(BaseModel):
    """Schema for listing cinemas with pagination."""
    total: int
    items: list[Cinema]
