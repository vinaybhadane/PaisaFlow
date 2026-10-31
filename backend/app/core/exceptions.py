"""Domain exceptions and standard error formats."""

from typing import Any, Dict, List, Optional
from fastapi import status


class PaisaFlowException(Exception):
    """Base exception for all PaisaFlow domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class NotFoundError(PaisaFlowException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(PaisaFlowException):
    """Raised when user input fails domain validation."""

    def __init__(self, message: str = "Validation failed", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationError(PaisaFlowException):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(self, message: str = "Authentication required", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(PaisaFlowException):
    """Raised when a user lacks permission for a resource."""

    def __init__(self, message: str = "Permission denied", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ConflictError(PaisaFlowException):
    """Raised on state conflicts such as duplicate resources."""

    def __init__(self, message: str = "Resource conflict", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class DatabaseUnavailableError(PaisaFlowException):
    """Raised when database connectivity cannot be established."""

    def __init__(self, message: str = "Database service currently unavailable", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


# Backward-compatible aliases
NotFoundException = NotFoundError
ValidationException = ValidationError


