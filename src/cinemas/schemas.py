from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CinemaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Cinema name")
    city: str = Field(..., min_length=1, max_length=255, description="City location")


class CinemaCreate(CinemaBase):
    pass


class Cinema(CinemaBase):
    cinema_id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CinemaList(BaseModel):
    total: int
    items: list[Cinema]
