"""Cinemas domain API endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends

from src.config import AppConfig, Constants
from src.database import get_pool
from src.exceptions import CinemaAPIException, DuplicateResourceException, DatabaseException
from .schemas import Cinema, CinemaCreate
from .service import CinemaService
from .dependencies import get_valid_cinema

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{AppConfig.API_PREFIX}/cinemas",
    tags=["Cinemas"]
)


@router.post(
    "",
    response_model=Cinema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new cinema",
    description="Create a new cinema with name and city. Name+City combination must be unique."
)
async def create_cinema(cinema_data: CinemaCreate):
    """Create a new cinema."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            # Check for duplicate
            await ctx.cursor.execute(
                "SELECT cinema_id FROM cinemas WHERE name = %s AND city = %s",
                (cinema_data.name, cinema_data.city)
            )
            if await ctx.cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cinema '{cinema_data.name}' in '{cinema_data.city}' already exists"
                )
            
            # Insert
            await ctx.cursor.execute(
                """INSERT INTO cinemas (name, city) 
                   VALUES (%s, %s) 
                   RETURNING cinema_id, name, city, created_at""",
                (cinema_data.name, cinema_data.city)
            )
            row = await ctx.cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create cinema"
                )
            
            return Cinema(
                cinema_id=row[0],
                name=row[1],
                city=row[2],
                created_at=row[3]
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cinema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cinema"
        )


@router.get(
    "",
    response_model=dict,
    summary="List all cinemas",
    description="List cinemas with pagination and optional city filter. Returns {total, items}"
)
async def list_cinemas(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(Constants.DEFAULT_LIMIT, ge=1, le=Constants.MAX_LIMIT, description="Number of items to return"),
    city: Optional[str] = Query(None, description="Filter by city (optional)")
):
    """List cinemas with pagination."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            total, cinemas = await CinemaService.list_cinemas(conn, skip, limit, city)
            return {
                "total": total,
                "skip": skip,
                "limit": limit,
                "items": cinemas
            }
    except Exception as e:
        logger.error(f"Error listing cinemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cinemas"
        )


@router.get(
    "/{cinema_id}",
    response_model=Cinema,
    summary="Get cinema by ID",
    description="Retrieve a specific cinema by its ID."
)
async def get_cinema(cinema: Cinema = Depends(get_valid_cinema)):
    """Get a specific cinema by ID."""
    return cinema
