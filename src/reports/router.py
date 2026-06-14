"""Reports domain - ciezkie raporty analityczne (do wywolania breaking pointa)."""
import logging

from fastapi import APIRouter, HTTPException, status, Query

from src.config import AppConfig
from src.database import get_pool
from src.exceptions import CinemaAPIException
from .service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{AppConfig.API_PREFIX}/reports", tags=["Reports"])

# sample_pct: % losowych stron tabeli biletow (TABLESAMPLE). 100 = pelny skan (najciezej).
SamplePct = Query(100, ge=1, le=100, description="Procent stron tabeli biletow do przeskanowania (TABLESAMPLE)")


def _handle(exc: Exception):
    if isinstance(exc, CinemaAPIException):
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    logger.error(f"Report error: {exc}")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Report failed")


@router.get("/revenue-by-city", response_model=list, summary="Przychod wg miasta (HEAVY: pelny skan biletow)")
async def revenue_by_city(sample_pct: int = SamplePct):
    try:
        async with get_pool().acquire() as conn:
            return await ReportService.revenue_by_city(conn, sample_pct)
    except Exception as e:
        _handle(e)


@router.get("/top-movies", response_model=list, summary="Top filmy wg sprzedazy (HEAVY: pelny skan biletow)")
async def top_movies(sample_pct: int = SamplePct):
    try:
        async with get_pool().acquire() as conn:
            return await ReportService.top_movies(conn, sample_pct)
    except Exception as e:
        _handle(e)


@router.get("/occupancy", response_model=dict, summary="Obciazenie seansow (HEAVY: skan + GROUP BY ~200k => spill)")
async def occupancy(sample_pct: int = SamplePct):
    try:
        async with get_pool().acquire() as conn:
            return await ReportService.occupancy(conn, sample_pct)
    except Exception as e:
        _handle(e)


# ---- SREDNIE raporty: podatne na zlamanie, ale nie "wyskakuja w kosmos" -----------
@router.get("/showtime/{showtime_id}/stats", response_model=dict, summary="Sprzedaz seansu (MEDIUM)")
async def showtime_stats(showtime_id: int):
    try:
        async with get_pool().acquire() as conn:
            return await ReportService.showtime_stats(conn, showtime_id)
    except Exception as e:
        _handle(e)


@router.get("/movie/{movie_id}/stats", response_model=dict, summary="Sprzedaz filmu po seansach (MEDIUM)")
async def movie_stats(movie_id: int):
    try:
        async with get_pool().acquire() as conn:
            return await ReportService.movie_stats(conn, movie_id)
    except Exception as e:
        _handle(e)
