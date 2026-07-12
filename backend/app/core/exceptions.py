"""
Custom exception classes for ResolveAI application.
Provides structured error handling with specific exception types instead of bare Exception.
"""

from fastapi import HTTPException, status


class ResolveAIException(Exception):
    """Base exception for all ResolveAI-specific errors"""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ExternalServiceError(ResolveAIException):
    """Raised when external API calls fail (NVIDIA NIM, OpenAI, etc.)"""
    def __init__(self, service_name: str, message: str):
        super().__init__(
            message=f"{service_name} service error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR"
        )


class EmbeddingServiceError(ExternalServiceError):
    """Raised when embedding generation fails"""
    def __init__(self, message: str):
        super().__init__(service_name="Embedding", message=message)


class LLMServiceError(ExternalServiceError):
    """Raised when LLM API calls fail"""
    def __init__(self, message: str):
        super().__init__(service_name="LLM", message=message)


class DatabaseError(ResolveAIException):
    """Raised when database operations fail"""
    def __init__(self, message: str):
        super().__init__(
            message=f"Database error: {message}",
            error_code="DATABASE_ERROR"
        )


class ValidationError(ResolveAIException):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: str = None):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(message=message, error_code=error_code)


class AuthenticationError(ResolveAIException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(ResolveAIException):
    """Raised when user lacks required permissions"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR"
        )


class ResourceNotFoundError(ResolveAIException):
    """Raised when requested resource doesn't exist"""
    def __init__(self, resource_type: str, resource_id: any):
        super().__init__(
            message=f"{resource_type} with id {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND"
        )


class DuplicateResourceError(ResolveAIException):
    """Raised when attempting to create duplicate resource"""
    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} with {identifier} already exists",
            error_code="DUPLICATE_RESOURCE"
        )


def exception_to_http_exception(exc: ResolveAIException) -> HTTPException:
    """
    Converts ResolveAI exceptions to FastAPI HTTPException.
    Maps error codes to appropriate HTTP status codes.
    """
    status_code_map = {
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR_TITLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR_CONTENT": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR_EMAIL": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR_PASSWORD": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "DUPLICATE_RESOURCE": status.HTTP_409_CONFLICT,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    http_status = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return HTTPException(
        status_code=http_status,
        detail={
            "message": exc.message,
            "error_code": exc.error_code
        }
    )
