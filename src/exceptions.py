"""Custom application exceptions."""
from typing import Any, Dict, Optional


class CinemaAPIException(Exception):
    """Base exception for Cinema API."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class ValidationException(CinemaAPIException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, detail=detail)


class ResourceNotFoundException(CinemaAPIException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any):
        message = f"{resource_type} with id {resource_id} not found"
        super().__init__(message, status_code=404)


class DuplicateResourceException(CinemaAPIException):
    """Raised when trying to create a duplicate resource."""
    
    def __init__(self, resource_type: str, field: str, value: Any):
        message = f"{resource_type} with {field}='{value}' already exists"
        super().__init__(message, status_code=409)


class ConflictException(CinemaAPIException):
    """Raised when operation conflicts with current state."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class InsufficientAvailabilityException(CinemaAPIException):
    """Raised when seats or resources are not available."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class TransactionException(CinemaAPIException):
    """Raised when transaction operation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class ReservationExpiredException(CinemaAPIException):
    """Raised when reservation has expired."""
    
    def __init__(self, reservation_id: int):
        message = f"Reservation {reservation_id} has expired"
        super().__init__(message, status_code=410)


class PaymentFailedException(CinemaAPIException):
    """Raised when payment fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=402)


class UnauthorizedException(CinemaAPIException):
    """Raised when operation is unauthorized."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class InvalidStateException(CinemaAPIException):
    """Raised when operation is invalid for current state."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class DatabaseException(CinemaAPIException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=500)
