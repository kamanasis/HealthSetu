"""Centralized error handling and exception definitions."""

from enum import Enum
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_ctx_var

logger = get_logger("app.exceptions")


class ErrorCode(str, Enum):
    """Standardized error codes for application responses."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Phase 8: Triage & SBAR Error Codes
    TRIAGE_INVALID_INPUT = "TRIAGE_INVALID_INPUT"
    TRIAGE_INSUFFICIENT_INFORMATION = "TRIAGE_INSUFFICIENT_INFORMATION"
    TRIAGE_RULE_ENGINE_UNAVAILABLE = "TRIAGE_RULE_ENGINE_UNAVAILABLE"
    TRIAGE_RULE_EVALUATION_FAILED = "TRIAGE_RULE_EVALUATION_FAILED"
    TRIAGE_RULE_NOT_SUPPORTED = "TRIAGE_RULE_NOT_SUPPORTED"
    TRIAGE_ASSESSMENT_NOT_FOUND = "TRIAGE_ASSESSMENT_NOT_FOUND"
    TRIAGE_ACCESS_DENIED = "TRIAGE_ACCESS_DENIED"
    SBAR_GENERATION_FAILED = "SBAR_GENERATION_FAILED"
    SBAR_VALIDATION_FAILED = "SBAR_VALIDATION_FAILED"
    SBAR_NOT_FOUND = "SBAR_NOT_FOUND"
    SYMPTOM_NOT_FOUND = "SYMPTOM_NOT_FOUND"


class AppException(Exception):
    """Base application exception for all domain and operational errors."""

    def __init__(
        self,
        code: ErrorCode | str = ErrorCode.INTERNAL_ERROR,
        message: str = "An unexpected error occurred.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code if isinstance(code, str) else code.value
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundException(AppException):
    """Resource not found exception (HTTP 404)."""

    def __init__(self, message: str = "Resource not found.", details: Any = None) -> None:
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class UnauthorizedException(AppException):
    """Authentication required or failed exception (HTTP 401)."""

    def __init__(self, message: str = "Authentication required.", details: Any = None) -> None:
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenException(AppException):
    """Action forbidden exception (HTTP 403)."""

    def __init__(self, message: str = "Access forbidden.", details: Any = None) -> None:
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ConflictException(AppException):
    """Conflict with current state exception (HTTP 409)."""

    def __init__(self, message: str = "Resource conflict.", details: Any = None) -> None:
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationException(AppException):
    """Input validation exception (HTTP 422)."""

    def __init__(self, message: str = "Validation failed.", details: Any = None) -> None:
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class ServiceUnavailableException(AppException):
    """Service unavailable exception (HTTP 503)."""

    def __init__(self, message: str = "Service temporarily unavailable.", details: Any = None) -> None:
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


def _get_request_id(request: Request) -> str:
    """Retrieve request ID from request state or context variable."""
    return getattr(request.state, "request_id", None) or request_id_ctx_var.get() or "unknown"


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
) -> JSONResponse:
    """Construct a standardized JSON error response."""
    error_payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if details is not None:
        error_payload["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={
            "success": false if False else False,
            "error": error_payload,
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    req_id = _get_request_id(request)
    logger.warning(
        f"Application exception: code={exc.code}, message={exc.message}",
        extra={"request_id": req_id, "status_code": exc.status_code},
    )
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=req_id,
        details=exc.details,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI / Pydantic request validation errors."""
    req_id = _get_request_id(request)
    # Simplify error details without leaking system internals
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append({"field": loc, "message": msg})

    logger.info(
        f"Validation error: {errors}",
        extra={"request_id": req_id, "status_code": 422},
    )
    return build_error_response(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR.value,
        message="Request validation failed.",
        request_id=req_id,
        details=errors,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette / FastAPI HTTPExceptions (such as 404, 405)."""
    req_id = _get_request_id(request)
    
    code_map: dict[int, str] = {
        status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND.value,
        status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED.value,
        status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN.value,
        status.HTTP_409_CONFLICT: ErrorCode.CONFLICT.value,
        status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE.value,
    }
    code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR.value)

    return build_error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail) if exc.detail else "An error occurred.",
        request_id=req_id,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions to prevent stack trace leakage."""
    req_id = _get_request_id(request)
    # Log internal stack trace securely with request_id
    logger.exception(
        f"Unhandled internal server error: {exc}",
        extra={"request_id": req_id, "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR},
    )
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR.value,
        message="An unexpected error occurred.",
        request_id=req_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers to the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
