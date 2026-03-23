from fastapi import FastAPI, HTTPException, Query, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import psycopg
import os

app = FastAPI(title="Cinema Reservation API", version="1.0.0", openapi_url="/api/v1/openapi.json")

DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "dbname": os.getenv("DB_NAME", "kino"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "pswd"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

RESERVATION_TIMEOUT_MINUTES = 15

def get_db_connection():
    return psycopg.connect(**DATABASE_CONFIG)

def cancel_expired_reservations(cur):
    timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_TIMEOUT_MINUTES)
    cur.execute(
        "UPDATE reservations SET status = 'cancelled' WHERE status = 'pending' AND created_at < %s",
        (timeout_threshold,)
    )


class Cinema(BaseModel):
    cinema_id: int
    name: str
    city: str

class CinemaCreate(BaseModel):
    name: str
    city: str

class User(BaseModel):
    user_id: int
    email: EmailStr
    username: str

class UserCreate(BaseModel):
    email: EmailStr
    username: str

class Hall(BaseModel):
    hall_id: int
    cinema_id: int
    hall_type_id: int
    name: str
    capacity: int

class HallCreate(BaseModel):
    cinema_id: int
    hall_type_id: int
    name: str
    capacity: int

class Reservation(BaseModel):
    reservation_id: int
    user_id: int
    showtime_id: int
    status: str
    created_at: Optional[datetime] = None

class ReservationCreate(BaseModel):
    user_id: int
    showtime_id: int
    seat_ids: List[int]

class ReservationStatusUpdate(BaseModel):
    status: str

class Seat(BaseModel):
    seat_id: int
    hall_id: int
    seat_type_id: int
    row_label: str
    seat_number: int

class SeatCreate(BaseModel):
    hall_id: int
    seat_type_id: int
    row_label: str
    seat_number: int

class SeatAvailability(BaseModel):
    seat_id: int
    hall_id: int
    seat_type_id: int
    seat_type_name: str
    row_label: str
    seat_number: int
    is_available: bool

class Movie(BaseModel):
    movie_id: int
    title: str
    duration_minutes: int

class MovieCreate(BaseModel):
    title: str
    duration_minutes: int

class Genre(BaseModel):
    genre_id: int
    name: str

class GenreCreate(BaseModel):
    name: str

class Showtime(BaseModel):
    showtime_id: int
    movie_id: int
    hall_id: int
    start_datetime: datetime
    base_price: float

class ShowtimeCreate(BaseModel):
    movie_id: int
    hall_id: int
    start_datetime: datetime
    base_price: float

class Ticket(BaseModel):
    ticket_id: int
    showtime_id: int
    seat_id: int
    user_id: int
    reservation_id: int
    ticket_group_id: int
    promotion_id: Optional[int]
    final_price: float
    status: str

class TicketCreate(BaseModel):
    showtime_id: int
    seat_id: int
    user_id: int
    reservation_id: int
    ticket_group_id: int
    promotion_id: Optional[int]
    final_price: float
    status: str

class Payment(BaseModel):
    payment_id: int
    user_id: int
    payment_method_id: int
    amount: float
    status: str

class PaymentCreate(BaseModel):
    user_id: int
    payment_method_id: int
    amount: float
    status: str

class PurchaseTicketRequest(BaseModel):
    reservation_id: int
    user_id: int
    payment_method_id: int
    ticket_group_id: int
    promotion_id: Optional[int] = None

class UserTicketHistory(BaseModel):
    ticket_id: int
    showtime_id: int
    seat_id: int
    reservation_id: int
    ticket_group_id: int
    promotion_id: Optional[int]
    final_price: float
    status: str
    movie_title: str
    showtime_start: datetime
    cinema_name: str
    city: str
    row_label: str
    seat_number: int
    created_at: Optional[datetime] = None

class UserReservationHistory(BaseModel):
    reservation_id: int
    showtime_id: int
    status: str
    created_at: Optional[datetime]
    movie_title: str
    showtime_start: datetime
    cinema_name: str
    seat_ids: List[int]

class UserPaymentHistory(BaseModel):
    payment_id: int
    payment_method_id: int
    payment_method_name: str
    amount: float
    status: str
    created_at: Optional[datetime]

class UserRefundHistory(BaseModel):
    refund_id: int
    ticket_id: int
    payment_id: int
    policy_id: int
    policy_name: str
    refund_amount: float
    created_at: Optional[datetime]

class SalesReportEntry(BaseModel):
    movie_id: int
    movie_title: str
    showtime_id: int
    showtime_start: datetime
    payment_method_id: int
    payment_method_name: str
    total_revenue: float
    tickets_sold: int

class SalesReportSummary(BaseModel):
    period_from: Optional[datetime]
    period_to: Optional[datetime]
    total_revenue: float
    total_tickets_sold: int
    breakdown: List[SalesReportEntry]


@app.post("/api/v1/users", response_model=User, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, username) VALUES (%s, %s) RETURNING user_id, email, username",
                (user.email, user.username)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="User registration failed")
            return User(user_id=row[0], email=row[1], username=row[2])


@app.get("/api/v1/users/{user_id}/tickets", response_model=List[UserTicketHistory])
def get_user_ticket_history(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT
                    t.ticket_id,
                    t.showtime_id,
                    t.seat_id,
                    t.reservation_id,
                    t.ticket_group_id,
                    t.promotion_id,
                    t.final_price,
                    t.status,
                    m.title AS movie_title,
                    s.start_datetime AS showtime_start,
                    c.name AS cinema_name,
                    c.city,
                    se.row_label,
                    se.seat_number,
                    t.created_at
                FROM tickets t
                JOIN showtimes s ON t.showtime_id = s.showtime_id
                JOIN movies m ON s.movie_id = m.movie_id
                JOIN halls h ON s.hall_id = h.hall_id
                JOIN cinemas c ON h.cinema_id = c.cinema_id
                JOIN seats se ON t.seat_id = se.seat_id
                WHERE t.user_id = %s
            """
            params = [user_id]
            if from_datetime:
                query += " AND t.created_at >= %s"
                params.append(from_datetime)
            if to_datetime:
                query += " AND t.created_at <= %s"
                params.append(to_datetime)
            query += " ORDER BY t.ticket_id DESC OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                UserTicketHistory(
                    ticket_id=row[0], showtime_id=row[1], seat_id=row[2],
                    reservation_id=row[3], ticket_group_id=row[4], promotion_id=row[5],
                    final_price=float(row[6]), status=row[7], movie_title=row[8],
                    showtime_start=row[9], cinema_name=row[10], city=row[11],
                    row_label=row[12], seat_number=row[13], created_at=row[14]
                ) for row in rows
            ]


@app.get("/api/v1/users/{user_id}/reservations", response_model=List[UserReservationHistory])
def get_user_reservation_history(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    reservation_status: Optional[str] = None,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cancel_expired_reservations(cur)
            query = """
                SELECT
                    r.reservation_id,
                    r.showtime_id,
                    r.status,
                    r.created_at,
                    m.title AS movie_title,
                    s.start_datetime AS showtime_start,
                    c.name AS cinema_name
                FROM reservations r
                JOIN showtimes s ON r.showtime_id = s.showtime_id
                JOIN movies m ON s.movie_id = m.movie_id
                JOIN halls h ON s.hall_id = h.hall_id
                JOIN cinemas c ON h.cinema_id = c.cinema_id
                WHERE r.user_id = %s
            """
            params = [user_id]
            if reservation_status:
                query += " AND r.status = %s"
                params.append(reservation_status)
            if from_datetime:
                query += " AND r.created_at >= %s"
                params.append(from_datetime)
            if to_datetime:
                query += " AND r.created_at <= %s"
                params.append(to_datetime)
            query += " ORDER BY r.reservation_id DESC OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            rows = cur.fetchall()
            result = []
            for row in rows:
                cur.execute(
                    "SELECT seat_id FROM reservation_seats WHERE reservation_id = %s",
                    (row[0],)
                )
                seat_ids = [seat_row[0] for seat_row in cur.fetchall()]
                result.append(UserReservationHistory(
                    reservation_id=row[0], showtime_id=row[1], status=row[2],
                    created_at=row[3], movie_title=row[4], showtime_start=row[5],
                    cinema_name=row[6], seat_ids=seat_ids
                ))
            return result


@app.get("/api/v1/users/{user_id}/payments", response_model=List[UserPaymentHistory])
def get_user_payment_history(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT
                    p.payment_id,
                    p.payment_method_id,
                    pm.name AS payment_method_name,
                    p.amount,
                    p.status,
                    p.created_at
                FROM payments p
                JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
                WHERE p.user_id = %s
            """
            params = [user_id]
            if from_datetime:
                query += " AND p.created_at >= %s"
                params.append(from_datetime)
            if to_datetime:
                query += " AND p.created_at <= %s"
                params.append(to_datetime)
            query += " ORDER BY p.payment_id DESC OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                UserPaymentHistory(
                    payment_id=row[0], payment_method_id=row[1], payment_method_name=row[2],
                    amount=float(row[3]), status=row[4], created_at=row[5]
                ) for row in rows
            ]


@app.get("/api/v1/users/{user_id}/refunds", response_model=List[UserRefundHistory])
def get_user_refund_history(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT
                    rf.refund_id,
                    rf.ticket_id,
                    rf.payment_id,
                    rf.policy_id,
                    cp.name AS policy_name,
                    rf.refund_amount,
                    rf.created_at
                FROM refunds rf
                JOIN tickets t ON rf.ticket_id = t.ticket_id
                JOIN cancellation_policies cp ON rf.policy_id = cp.policy_id
                WHERE t.user_id = %s
            """
            params = [user_id]
            if from_datetime:
                query += " AND rf.created_at >= %s"
                params.append(from_datetime)
            if to_datetime:
                query += " AND rf.created_at <= %s"
                params.append(to_datetime)
            query += " ORDER BY rf.refund_id DESC OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                UserRefundHistory(
                    refund_id=row[0], ticket_id=row[1], payment_id=row[2],
                    policy_id=row[3], policy_name=row[4],
                    refund_amount=float(row[5]), created_at=row[6]
                ) for row in rows
            ]


@app.get("/api/v1/cinemas", response_model=List[Cinema])
def list_cinemas(skip: int = 0, limit: int = 20, city: Optional[str] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT cinema_id, name, city FROM cinemas"
            params = []
            if city:
                query += " WHERE city = %s"
                params.append(city)
            query += " ORDER BY cinema_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Cinema(cinema_id=row[0], name=row[1], city=row[2]) for row in cur.fetchall()]

@app.post("/api/v1/cinemas", response_model=Cinema, status_code=status.HTTP_201_CREATED)
def create_cinema(cinema: CinemaCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO cinemas (name, city) VALUES (%s, %s) RETURNING cinema_id, name, city",
                (cinema.name, cinema.city)
            )
            row = cur.fetchone()
            return Cinema(cinema_id=row[0], name=row[1], city=row[2])


@app.get("/api/v1/halls", response_model=List[Hall])
def list_halls(skip: int = 0, limit: int = 20, cinema_id: Optional[int] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT hall_id, cinema_id, hall_type_id, name, capacity FROM halls"
            params = []
            if cinema_id:
                query += " WHERE cinema_id = %s"
                params.append(cinema_id)
            query += " ORDER BY hall_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Hall(hall_id=row[0], cinema_id=row[1], hall_type_id=row[2], name=row[3], capacity=row[4]) for row in cur.fetchall()]

@app.post("/api/v1/halls", response_model=Hall, status_code=status.HTTP_201_CREATED)
def create_hall(hall: HallCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO halls (cinema_id, hall_type_id, name, capacity) VALUES (%s, %s, %s, %s) RETURNING hall_id, cinema_id, hall_type_id, name, capacity",
                (hall.cinema_id, hall.hall_type_id, hall.name, hall.capacity)
            )
            row = cur.fetchone()
            return Hall(hall_id=row[0], cinema_id=row[1], hall_type_id=row[2], name=row[3], capacity=row[4])


@app.get("/api/v1/showtimes/{showtime_id}/seats", response_model=List[SeatAvailability])
def get_showtime_seat_availability(showtime_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cancel_expired_reservations(cur)
            cur.execute("SELECT hall_id FROM showtimes WHERE showtime_id = %s", (showtime_id,))
            showtime_row = cur.fetchone()
            if not showtime_row:
                raise HTTPException(status_code=404, detail="Showtime not found")
            hall_id = showtime_row[0]
            query = """
                SELECT
                    se.seat_id,
                    se.hall_id,
                    se.seat_type_id,
                    st.name AS seat_type_name,
                    se.row_label,
                    se.seat_number,
                    CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM reservation_seats rs
                            JOIN reservations r ON rs.reservation_id = r.reservation_id
                            WHERE rs.seat_id = se.seat_id
                              AND r.showtime_id = %s
                              AND r.status IN ('pending', 'confirmed')
                        ) THEN FALSE
                        WHEN EXISTS (
                            SELECT 1
                            FROM tickets t
                            WHERE t.seat_id = se.seat_id
                              AND t.showtime_id = %s
                              AND t.status = 'valid'
                        ) THEN FALSE
                        ELSE TRUE
                    END AS is_available
                FROM seats se
                JOIN seat_types st ON se.seat_type_id = st.seat_type_id
                WHERE se.hall_id = %s
                ORDER BY se.row_label, se.seat_number
            """
            cur.execute(query, (showtime_id, showtime_id, hall_id))
            rows = cur.fetchall()
            return [
                SeatAvailability(
                    seat_id=row[0], hall_id=row[1], seat_type_id=row[2],
                    seat_type_name=row[3], row_label=row[4], seat_number=row[5],
                    is_available=row[6]
                ) for row in rows
            ]


@app.post("/api/v1/reservations", response_model=Reservation, status_code=status.HTTP_201_CREATED)
def create_reservation(reservation: ReservationCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cancel_expired_reservations(cur)
            cur.execute("SELECT showtime_id FROM showtimes WHERE showtime_id = %s", (reservation.showtime_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Showtime not found")
            for seat_id in reservation.seat_ids:
                cur.execute("""
                    SELECT 1
                    FROM reservation_seats rs
                    JOIN reservations r ON rs.reservation_id = r.reservation_id
                    WHERE rs.seat_id = %s
                      AND r.showtime_id = %s
                      AND r.status IN ('pending', 'confirmed')
                """, (seat_id, reservation.showtime_id))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail=f"Seat {seat_id} is already reserved for this showtime")
                cur.execute("""
                    SELECT 1 FROM tickets
                    WHERE seat_id = %s AND showtime_id = %s AND status = 'valid'
                """, (seat_id, reservation.showtime_id))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail=f"Seat {seat_id} already has a valid ticket for this showtime")
            cur.execute(
                "INSERT INTO reservations (user_id, showtime_id, status, created_at) VALUES (%s, %s, 'pending', %s) RETURNING reservation_id, user_id, showtime_id, status, created_at",
                (reservation.user_id, reservation.showtime_id, datetime.now(timezone.utc))
            )
            row = cur.fetchone()
            reservation_id = row[0]
            for seat_id in reservation.seat_ids:
                cur.execute(
                    "INSERT INTO reservation_seats (reservation_id, seat_id) VALUES (%s, %s)",
                    (reservation_id, seat_id)
                )
            conn.commit()
            return Reservation(reservation_id=row[0], user_id=row[1], showtime_id=row[2], status=row[3], created_at=row[4])


@app.get("/api/v1/reservations", response_model=List[Reservation])
def list_reservations(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = None,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cancel_expired_reservations(cur)
            query = "SELECT reservation_id, user_id, showtime_id, status, created_at FROM reservations"
            params = []
            filters = []
            if user_id:
                filters.append("user_id = %s")
                params.append(user_id)
            if from_datetime:
                filters.append("created_at >= %s")
                params.append(from_datetime)
            if to_datetime:
                filters.append("created_at <= %s")
                params.append(to_datetime)
            if filters:
                query += " WHERE " + " AND ".join(filters)
            query += " ORDER BY reservation_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Reservation(reservation_id=row[0], user_id=row[1], showtime_id=row[2], status=row[3], created_at=row[4]) for row in cur.fetchall()]


@app.put("/api/v1/reservations/{reservation_id}/status", response_model=Reservation)
def update_reservation_status(reservation_id: int, status_update: ReservationStatusUpdate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE reservations SET status = %s WHERE reservation_id = %s RETURNING reservation_id, user_id, showtime_id, status, created_at",
                (status_update.status, reservation_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Reservation not found")
            conn.commit()
            return Reservation(reservation_id=row[0], user_id=row[1], showtime_id=row[2], status=row[3], created_at=row[4])


@app.delete("/api/v1/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(reservation_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT reservation_id FROM reservations WHERE reservation_id = %s", (reservation_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Reservation not found")
            cur.execute("DELETE FROM reservation_seats WHERE reservation_id = %s", (reservation_id,))
            cur.execute("DELETE FROM reservations WHERE reservation_id = %s", (reservation_id,))
            conn.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})


@app.post("/api/v1/tickets/purchase", response_model=Ticket)
def purchase_ticket(request: PurchaseTicketRequest):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT reservation_id, user_id, showtime_id, status, created_at FROM reservations WHERE reservation_id = %s",
                (request.reservation_id,)
            )
            reservation = cur.fetchone()
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation[3] != 'pending':
                raise HTTPException(status_code=400, detail="Reservation is not in pending status")
            timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_TIMEOUT_MINUTES)
            if reservation[4] < timeout_threshold:
                cur.execute(
                    "UPDATE reservations SET status = 'cancelled' WHERE reservation_id = %s",
                    (request.reservation_id,)
                )
                conn.commit()
                raise HTTPException(status_code=400, detail="Reservation expired and has been cancelled")
            cur.execute(
                "SELECT seat_id FROM reservation_seats WHERE reservation_id = %s",
                (request.reservation_id,)
            )
            seat_rows = cur.fetchall()
            if not seat_rows:
                raise HTTPException(status_code=400, detail="No seats found for this reservation")
            seat_id = seat_rows[0][0]
            cur.execute(
                "SELECT base_price FROM showtimes WHERE showtime_id = %s",
                (reservation[2],)
            )
            base_price_row = cur.fetchone()
            if not base_price_row:
                raise HTTPException(status_code=404, detail="Showtime not found")
            final_price = float(base_price_row[0])
            if request.promotion_id:
                cur.execute(
                    "SELECT discount_value FROM promotions WHERE promotion_id = %s",
                    (request.promotion_id,)
                )
                promo_row = cur.fetchone()
                if promo_row:
                    final_price = max(0.0, final_price - float(promo_row[0]))
            cur.execute("""
                INSERT INTO tickets
                    (showtime_id, seat_id, user_id, reservation_id, ticket_group_id, promotion_id, final_price, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'valid')
                RETURNING ticket_id, showtime_id, seat_id, user_id, reservation_id, ticket_group_id, promotion_id, final_price, status
            """, (reservation[2], seat_id, request.user_id, request.reservation_id, request.ticket_group_id, request.promotion_id, final_price))
            ticket_row = cur.fetchone()
            cur.execute(
                "UPDATE reservations SET status = 'confirmed' WHERE reservation_id = %s",
                (request.reservation_id,)
            )
            cur.execute(
                "INSERT INTO payments (user_id, payment_method_id, amount, status) VALUES (%s, %s, %s, 'completed') RETURNING payment_id",
                (request.user_id, request.payment_method_id, final_price)
            )
            payment_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO ticket_payments (ticket_id, payment_id, amount) VALUES (%s, %s, %s)",
                (ticket_row[0], payment_id, final_price)
            )
            conn.commit()
            return Ticket(
                ticket_id=ticket_row[0], showtime_id=ticket_row[1], seat_id=ticket_row[2],
                user_id=ticket_row[3], reservation_id=ticket_row[4], ticket_group_id=ticket_row[5],
                promotion_id=ticket_row[6], final_price=float(ticket_row[7]), status=ticket_row[8]
            )


@app.get("/api/v1/seats", response_model=List[Seat])
def list_seats(skip: int = 0, limit: int = 20, hall_id: Optional[int] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT seat_id, hall_id, seat_type_id, row_label, seat_number FROM seats"
            params = []
            if hall_id:
                query += " WHERE hall_id = %s"
                params.append(hall_id)
            query += " ORDER BY seat_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Seat(seat_id=row[0], hall_id=row[1], seat_type_id=row[2], row_label=row[3], seat_number=row[4]) for row in cur.fetchall()]

@app.post("/api/v1/seats", response_model=Seat, status_code=status.HTTP_201_CREATED)
def create_seat(seat: SeatCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO seats (hall_id, seat_type_id, row_label, seat_number) VALUES (%s, %s, %s, %s) RETURNING seat_id, hall_id, seat_type_id, row_label, seat_number",
                (seat.hall_id, seat.seat_type_id, seat.row_label, seat.seat_number)
            )
            row = cur.fetchone()
            conn.commit()
            return Seat(seat_id=row[0], hall_id=row[1], seat_type_id=row[2], row_label=row[3], seat_number=row[4])


@app.get("/api/v1/movies", response_model=List[Movie])
def list_movies(skip: int = 0, limit: int = 20, title: Optional[str] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT movie_id, title, duration_minutes FROM movies"
            params = []
            if title:
                query += " WHERE title ILIKE %s"
                params.append(f"%{title}%")
            query += " ORDER BY movie_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Movie(movie_id=row[0], title=row[1], duration_minutes=row[2]) for row in cur.fetchall()]

@app.post("/api/v1/movies", response_model=Movie, status_code=status.HTTP_201_CREATED)
def create_movie(movie: MovieCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO movies (title, duration_minutes) VALUES (%s, %s) RETURNING movie_id, title, duration_minutes",
                (movie.title, movie.duration_minutes)
            )
            row = cur.fetchone()
            conn.commit()
            return Movie(movie_id=row[0], title=row[1], duration_minutes=row[2])


@app.get("/api/v1/genres", response_model=List[Genre])
def list_genres(skip: int = 0, limit: int = 20, name: Optional[str] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT genre_id, name FROM genres"
            params = []
            if name:
                query += " WHERE name ILIKE %s"
                params.append(f"%{name}%")
            query += " ORDER BY genre_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Genre(genre_id=row[0], name=row[1]) for row in cur.fetchall()]

@app.post("/api/v1/genres", response_model=Genre, status_code=status.HTTP_201_CREATED)
def create_genre(genre: GenreCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO genres (name) VALUES (%s) RETURNING genre_id, name",
                (genre.name,)
            )
            row = cur.fetchone()
            conn.commit()
            return Genre(genre_id=row[0], name=row[1])


@app.get("/api/v1/showtimes", response_model=List[Showtime])
def list_showtimes(
    skip: int = 0,
    limit: int = 20,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None,
    movie_id: Optional[int] = None,
    hall_id: Optional[int] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT showtime_id, movie_id, hall_id, start_datetime, base_price FROM showtimes"
            params = []
            filters = []
            if from_datetime:
                filters.append("start_datetime >= %s")
                params.append(from_datetime)
            if to_datetime:
                filters.append("start_datetime <= %s")
                params.append(to_datetime)
            if movie_id:
                filters.append("movie_id = %s")
                params.append(movie_id)
            if hall_id:
                filters.append("hall_id = %s")
                params.append(hall_id)
            if filters:
                query += " WHERE " + " AND ".join(filters)
            query += " ORDER BY showtime_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Showtime(showtime_id=row[0], movie_id=row[1], hall_id=row[2], start_datetime=row[3], base_price=float(row[4])) for row in cur.fetchall()]

@app.post("/api/v1/showtimes", response_model=Showtime, status_code=status.HTTP_201_CREATED)
def create_showtime(showtime: ShowtimeCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO showtimes (movie_id, hall_id, start_datetime, base_price) VALUES (%s, %s, %s, %s) RETURNING showtime_id, movie_id, hall_id, start_datetime, base_price",
                (showtime.movie_id, showtime.hall_id, showtime.start_datetime, showtime.base_price)
            )
            row = cur.fetchone()
            conn.commit()
            return Showtime(showtime_id=row[0], movie_id=row[1], hall_id=row[2], start_datetime=row[3], base_price=float(row[4]))


@app.get("/api/v1/tickets", response_model=List[Ticket])
def list_tickets(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = None,
    reservation_id: Optional[int] = None,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT ticket_id, showtime_id, seat_id, user_id, reservation_id, ticket_group_id, promotion_id, final_price, status FROM tickets"
            params = []
            filters = []
            if user_id:
                filters.append("user_id = %s")
                params.append(user_id)
            if reservation_id:
                filters.append("reservation_id = %s")
                params.append(reservation_id)
            if from_datetime:
                filters.append("created_at >= %s")
                params.append(from_datetime)
            if to_datetime:
                filters.append("created_at <= %s")
                params.append(to_datetime)
            if filters:
                query += " WHERE " + " AND ".join(filters)
            query += " ORDER BY ticket_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Ticket(ticket_id=row[0], showtime_id=row[1], seat_id=row[2], user_id=row[3], reservation_id=row[4], ticket_group_id=row[5], promotion_id=row[6], final_price=float(row[7]), status=row[8]) for row in cur.fetchall()]

@app.post("/api/v1/tickets", response_model=Ticket, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket: TicketCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tickets
                    (showtime_id, seat_id, user_id, reservation_id, ticket_group_id, promotion_id, final_price, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING ticket_id, showtime_id, seat_id, user_id, reservation_id, ticket_group_id, promotion_id, final_price, status
            """, (ticket.showtime_id, ticket.seat_id, ticket.user_id, ticket.reservation_id,
                  ticket.ticket_group_id, ticket.promotion_id, ticket.final_price, ticket.status,
                  datetime.now(timezone.utc)))
            row = cur.fetchone()
            conn.commit()
            return Ticket(ticket_id=row[0], showtime_id=row[1], seat_id=row[2], user_id=row[3], reservation_id=row[4], ticket_group_id=row[5], promotion_id=row[6], final_price=float(row[7]), status=row[8])


@app.get("/api/v1/payments", response_model=List[Payment])
def list_payments(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = None,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT payment_id, user_id, payment_method_id, amount, status FROM payments"
            params = []
            filters = []
            if user_id:
                filters.append("user_id = %s")
                params.append(user_id)
            if from_datetime:
                filters.append("created_at >= %s")
                params.append(from_datetime)
            if to_datetime:
                filters.append("created_at <= %s")
                params.append(to_datetime)
            if filters:
                query += " WHERE " + " AND ".join(filters)
            query += " ORDER BY payment_id OFFSET %s LIMIT %s"
            params.extend([skip, limit])
            cur.execute(query, params)
            return [Payment(payment_id=row[0], user_id=row[1], payment_method_id=row[2], amount=float(row[3]), status=row[4]) for row in cur.fetchall()]

@app.post("/api/v1/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO payments (user_id, payment_method_id, amount, status, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING payment_id, user_id, payment_method_id, amount, status",
                (payment.user_id, payment.payment_method_id, payment.amount, payment.status, datetime.now(timezone.utc))
            )
            row = cur.fetchone()
            conn.commit()
            return Payment(payment_id=row[0], user_id=row[1], payment_method_id=row[2], amount=float(row[3]), status=row[4])


@app.get("/api/v1/reports/sales", response_model=SalesReportSummary)
def get_sales_report(
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT
                    m.movie_id,
                    m.title AS movie_title,
                    s.showtime_id,
                    s.start_datetime AS showtime_start,
                    pm.payment_method_id,
                    pm.name AS payment_method_name,
                    SUM(p.amount) AS total_revenue,
                    COUNT(t.ticket_id) AS tickets_sold
                FROM tickets t
                JOIN showtimes s ON t.showtime_id = s.showtime_id
                JOIN movies m ON s.movie_id = m.movie_id
                JOIN ticket_payments tp ON t.ticket_id = tp.ticket_id
                JOIN payments p ON tp.payment_id = p.payment_id
                JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
                WHERE t.status = 'valid'
                  AND p.status = 'completed'
            """
            params = []
            if from_datetime:
                query += " AND p.created_at >= %s"
                params.append(from_datetime)
            if to_datetime:
                query += " AND p.created_at <= %s"
                params.append(to_datetime)
            query += """
                GROUP BY m.movie_id, m.title, s.showtime_id, s.start_datetime, pm.payment_method_id, pm.name
                ORDER BY s.showtime_id, pm.payment_method_id
            """
            cur.execute(query, params)
            rows = cur.fetchall()
            breakdown = [
                SalesReportEntry(
                    movie_id=row[0], movie_title=row[1], showtime_id=row[2],
                    showtime_start=row[3], payment_method_id=row[4],
                    payment_method_name=row[5], total_revenue=float(row[6]),
                    tickets_sold=row[7]
                ) for row in rows
            ]
            total_revenue = sum(entry.total_revenue for entry in breakdown)
            total_tickets_sold = sum(entry.tickets_sold for entry in breakdown)
            return SalesReportSummary(
                period_from=from_datetime,
                period_to=to_datetime,
                total_revenue=total_revenue,
                total_tickets_sold=total_tickets_sold,
                breakdown=breakdown
            )