import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query

from src.config import AppConfig
from src.database import get_pool
from src.exceptions import DuplicateResourceException, DatabaseException
from .schemas import User, UserCreate
from .service import UserService
from .dependencies import get_valid_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{AppConfig.API_PREFIX}/users", tags=["Users"])


@router.post(
    "",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def register_user(user_data: UserCreate):
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            user = await UserService.create_user(ctx.connection, user_data)
            return user
    except DuplicateResourceException:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already registered")
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user")


@router.get("/{user_id}", response_model=User, summary="Get user by ID")
async def get_user(user: User = Depends(get_valid_user)):
    return user


@router.get("/{user_id}/reservations", response_model=dict, summary="Get user reservations")
async def get_user_reservations(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            await UserService.get_user_by_id(conn, user_id)
            
            async with conn.cursor() as cur:
                query = """
                    SELECT r.reservation_id, r.showtime_id, r.status, r.created_at,
                           m.title, s.start_datetime, c.name, c.city
                    FROM reservations r
                    JOIN showtimes s ON r.showtime_id = s.showtime_id
                    JOIN movies m ON s.movie_id = m.movie_id
                    JOIN halls h ON s.hall_id = h.hall_id
                    JOIN cinemas c ON h.cinema_id = c.cinema_id
                    WHERE r.user_id = %s
                    ORDER BY r.created_at DESC
                    OFFSET %s LIMIT %s
                """
                await cur.execute(query, (user_id, skip, limit))
                rows = await cur.fetchall()
                
                reservations = [
                    {
                        "reservation_id": row[0],
                        "showtime_id": row[1],
                        "status": row[2],
                        "created_at": row[3],
                        "movie_title": row[4],
                        "showtime_start": row[5],
                        "cinema_name": row[6],
                        "city": row[7]
                    }
                    for row in rows
                ]
                
                return {"total": len(reservations), "items": reservations}
    except Exception as e:
        logger.error(f"Error getting user reservations: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{user_id}/tickets", response_model=dict, summary="Get user tickets")
async def get_user_tickets(user_id: int, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            await UserService.get_user_by_id(conn, user_id)
            
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT t.ticket_id, t.showtime_id, t.seat_id, t.status, t.final_price,
                              m.title, s.start_datetime, c.name, se.row_label, se.seat_number, t.created_at
                       FROM tickets t
                       JOIN showtimes s ON t.showtime_id = s.showtime_id
                       JOIN movies m ON s.movie_id = m.movie_id
                       JOIN halls h ON s.hall_id = h.hall_id
                       JOIN cinemas c ON h.cinema_id = c.cinema_id
                       JOIN seats se ON t.seat_id = se.seat_id
                       WHERE t.user_id = %s
                       ORDER BY t.created_at DESC
                       OFFSET %s LIMIT %s""",
                    (user_id, skip, limit)
                )
                rows = await cur.fetchall()
                
                tickets = [
                    {
                        "ticket_id": row[0],
                        "showtime_id": row[1],
                        "seat_id": row[2],
                        "status": row[3],
                        "final_price": float(row[4]),
                        "movie_title": row[5],
                        "showtime_start": row[6],
                        "cinema_name": row[7],
                        "seat": f"{row[8]}{row[9]}",
                        "created_at": row[10]
                    }
                    for row in rows
                ]
                
                return {"total": len(tickets), "items": tickets}
    except Exception as e:
        logger.error(f"Error getting user tickets: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
