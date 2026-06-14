import logging

import psycopg

from src.exceptions import DatabaseException, CinemaAPIException

logger = logging.getLogger(__name__)

HEAVY_STATEMENT_TIMEOUT = "60s"


class QueryOverloadException(CinemaAPIException):
    def __init__(self, message: str = "Report query exceeded statement_timeout (DB overloaded)"):
        super().__init__(message, status_code=503)


class ReportService:
    @staticmethod
    async def _run(conn, sql: str, params=None, fetch: str = "all"):
        try:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(f"SET LOCAL statement_timeout = '{HEAVY_STATEMENT_TIMEOUT}'")
                    await cur.execute(sql, params)
                    cols = [d.name for d in cur.description]
                    if fetch == "one":
                        row = await cur.fetchone()
                        return dict(zip(cols, row)) if row else {}
                    rows = await cur.fetchall()
                    return [dict(zip(cols, r)) for r in rows]
        except psycopg.errors.QueryCanceled as e:
            logger.warning(f"Report query canceled (statement_timeout): {e}")
            raise QueryOverloadException()
        except psycopg.Error as e:
            logger.error(f"Report query DB error: {e}")
            raise DatabaseException(f"Report failed: {str(e)}")



    @staticmethod
    async def showtime_stats(conn, showtime_id: int) -> dict:
        sql = """
            SELECT sh.showtime_id,
                   sh.base_price,
                   count(t.ticket_id)                       AS sold,
                   coalesce(round(sum(t.final_price), 2), 0) AS revenue
            FROM showtimes sh
            LEFT JOIN tickets t
                   ON t.showtime_id = sh.showtime_id AND t.status = 'valid'
            WHERE sh.showtime_id = %s
            GROUP BY sh.showtime_id, sh.base_price
        """
        return await ReportService._run(conn, sql, (showtime_id,), fetch="one")

    @staticmethod
    async def movie_stats(conn, movie_id: int) -> dict:
        sql = """
            SELECT %s::int                                   AS movie_id,
                   count(*)                                  AS tickets,
                   coalesce(round(sum(t.final_price), 2), 0) AS revenue,
                   count(DISTINCT t.showtime_id)             AS showtimes
            FROM tickets t
            JOIN showtimes sh ON t.showtime_id = sh.showtime_id
            WHERE sh.movie_id = %s
        """
        return await ReportService._run(conn, sql, (movie_id, movie_id), fetch="one")

    @staticmethod
    async def revenue_by_city(conn, sample_pct: int) -> list[dict]:
        sql = f"""
            SELECT c.city,
                   count(*)                       AS tickets,
                   round(sum(t.final_price), 2)   AS revenue
            FROM tickets t TABLESAMPLE SYSTEM ({sample_pct})
            JOIN showtimes sh ON t.showtime_id = sh.showtime_id
            JOIN halls     h  ON sh.hall_id     = h.hall_id
            JOIN cinemas   c  ON h.cinema_id    = c.cinema_id
            WHERE t.status = 'valid'
            GROUP BY c.city
            ORDER BY revenue DESC NULLS LAST
            LIMIT 50
        """
        return await ReportService._run(conn, sql, fetch="all")

    @staticmethod
    async def top_movies(conn, sample_pct: int) -> list[dict]:
        sql = f"""
            SELECT m.movie_id, m.title,
                   count(*)                       AS tickets,
                   round(sum(t.final_price), 2)   AS revenue
            FROM tickets t TABLESAMPLE SYSTEM ({sample_pct})
            JOIN showtimes sh ON t.showtime_id = sh.showtime_id
            JOIN movies    m  ON sh.movie_id    = m.movie_id
            GROUP BY m.movie_id, m.title
            ORDER BY tickets DESC
            LIMIT 20
        """
        return await ReportService._run(conn, sql, fetch="all")

    @staticmethod
    async def occupancy(conn, sample_pct: int) -> dict:
        sql = f"""
            SELECT count(*)                 AS showtimes_counted,
                   round(avg(cnt), 2)       AS avg_tickets_per_showtime,
                   max(cnt)                 AS max_tickets_in_showtime
            FROM (
                SELECT showtime_id, count(*) AS cnt
                FROM tickets TABLESAMPLE SYSTEM ({sample_pct})
                GROUP BY showtime_id
            ) q
        """
        return await ReportService._run(conn, sql, fetch="one")
