import os
from typing import Optional

class DatabaseConfig:
    HOST: str = os.getenv("DB_HOST", "db")
    PORT: int = int(os.getenv("DB_PORT", "5432"))
    NAME: str = os.getenv("DB_NAME", "kino")
    USER: str = os.getenv("DB_USER", "postgres")
    PASSWORD: str = os.getenv("DB_PASSWORD", "pswd")

    MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "5"))
    MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
    MAX_OVERFLOW: int = int(os.getenv("DB_POOL_MAX_OVERFLOW", "10"))
    TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))

    ISOLATION_LEVEL: str = "REPEATABLE READ"

    @classmethod
    def get_connection_string(cls) -> str:
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.NAME}"

    @classmethod
    def get_admin_connection_string(cls) -> str:
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/postgres"


class AppConfig:
    API_VERSION: str = "v1"
    API_PREFIX: str = f"/api/{API_VERSION}"

    TITLE: str = "Cinema Reservation API"
    DESCRIPTION: str = "Advanced Cinema Reservation System with transactions"
    VERSION: str = "2.0.0"

    SHOW_DOCS: bool = os.getenv("ENVIRONMENT", "local") not in ("production", "staging")
    OPENAPI_URL: Optional[str] = "/api/v1/openapi.json" if SHOW_DOCS else None
    DOCS_URL: Optional[str] = "/docs" if SHOW_DOCS else None
    REDOC_URL: Optional[str] = "/redoc" if SHOW_DOCS else None

    RESERVATION_TIMEOUT_MINUTES: int = 15
    DB_QUERY_TIMEOUT: int = 30


class Constants:
    RESERVATION_STATUSES = {"pending", "confirmed", "cancelled"}
    TICKET_STATUSES = {"valid", "cancelled", "used"}
    PAYMENT_STATUSES = {"pending", "completed", "failed", "refunded"}

    DEFAULT_LIMIT: int = 20
    MAX_LIMIT: int = 100


database_config = DatabaseConfig()
app_config = AppConfig()
constants = Constants()
