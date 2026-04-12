"""Database connection pooling and transaction handling."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, NamedTuple

import psycopg
from psycopg import AsyncConnection, AsyncCursor
from psycopg_pool import AsyncConnectionPool

from src.config import DatabaseConfig

logger = logging.getLogger(__name__)


class TransactionContext(NamedTuple):
    """Context object for transactions containing both cursor and connection."""
    cursor: AsyncCursor
    connection: AsyncConnection


class DatabasePool:
    """Singleton for managing PostgreSQL connection pool."""
    
    _instance: Optional["DatabasePool"] = None
    _pool: Optional[AsyncConnectionPool] = None
    
    def __new__(cls) -> "DatabasePool":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            logger.warning("Pool already initialized")
            return
        
        try:
            self._pool = AsyncConnectionPool(
                conninfo=DatabaseConfig.get_connection_string(),
                min_size=DatabaseConfig.MIN_SIZE,
                max_size=DatabaseConfig.MAX_SIZE,
                max_idle=60,
                timeout=DatabaseConfig.TIMEOUT,
            )
            await self._pool.wait()
            logger.info(f"Database pool initialized: min={DatabaseConfig.MIN_SIZE}, max={DatabaseConfig.MAX_SIZE}")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")
    
    async def get_connection(self) -> AsyncConnection:
        """Get a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        return await self._pool.getconn()
    
    async def return_connection(self, conn: AsyncConnection) -> None:
        """Return a connection to the pool."""
        if self._pool:
            await self._pool.putconn(conn)
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[AsyncConnection]:
        """Context manager for acquiring and returning connection."""
        conn = await self.get_connection()
        try:
            # Set isolation level
            await conn.set_isolation_level(
                psycopg.IsolationLevel.repeatable_read
            )
            yield conn
        finally:
            await self.return_connection(conn)
    
    @asynccontextmanager
    async def transaction(
        self, 
        conn: Optional[AsyncConnection] = None
    ) -> AsyncIterator[TransactionContext]:
        """Context manager for transactions with proper ACID guarantees.
        
        Automatically handles BEGIN/COMMIT/ROLLBACK.
        Yields a TransactionContext object with both cursor and connection.
        """
        if conn is None:
            conn = await self.get_connection()
            should_return = True
        else:
            should_return = False
        
        try:
            # Set isolation level and begin transaction
            await conn.set_isolation_level(
                psycopg.IsolationLevel.repeatable_read
            )
            async with conn.transaction():
                async with conn.cursor() as cur:
                    yield TransactionContext(cursor=cur, connection=conn)
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            raise
        finally:
            if should_return:
                await self.return_connection(conn)


# Global pool instance
_pool = DatabasePool()


async def init_db() -> None:
    """Initialize database pool (call on app startup)."""
    await _pool.initialize()


async def close_db() -> None:
    """Close database pool (call on app shutdown)."""
    await _pool.close()


async def get_db_connection() -> AsyncConnection:
    """Get a database connection from the pool."""
    return await _pool.get_connection()


def get_pool() -> DatabasePool:
    """Get the database pool instance."""
    return _pool
