"""Main FastAPI application entry point."""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.config import AppConfig
from src.database import init_db, close_db
from src.database_init import initialize_database
from src.exceptions import CinemaAPIException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import routers
from src.cinemas import router as cinemas_router
from src.users import router as users_router
from src.reservations import router as reservations_router
from src.tickets import router as tickets_router
from src.payments import router as payments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("Starting up Cinema API...")
    try:
        # Initialize database schema (one-time, synchronous)
        await initialize_database()
        logger.info("Database initialized")
        
        # Initialize async connection pool
        await init_db()
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cinema API...")
    await close_db()
    logger.info("Database pool closed")


# Create FastAPI application
app = FastAPI(
    title=AppConfig.TITLE,
    description=AppConfig.DESCRIPTION,
    version=AppConfig.VERSION,
    openapi_url=AppConfig.OPENAPI_URL,
    docs_url=AppConfig.DOCS_URL,
    redoc_url=AppConfig.REDOC_URL,
    lifespan=lifespan
)


# Exception handler for custom exceptions
@app.exception_handler(CinemaAPIException)
async def handle_cinema_exception(request, exc: CinemaAPIException):
    """Handle custom Cinema API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail or "An error occurred"
        }
    )


# Include routers
app.include_router(cinemas_router)
app.include_router(users_router)
app.include_router(reservations_router)
app.include_router(tickets_router)
app.include_router(payments_router)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Cinema Reservation API"}


# Root endpoint with API info
@app.get("/", tags=["Info"])
async def root():
    """API root endpoint with service information."""
    return {
        "name": AppConfig.TITLE,
        "version": AppConfig.VERSION,
        "description": AppConfig.DESCRIPTION,
        "docs": "/docs" if AppConfig.SHOW_DOCS else "Not available",
        "api_prefix": AppConfig.API_PREFIX
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
