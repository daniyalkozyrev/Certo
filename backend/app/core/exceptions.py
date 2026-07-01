"""Domain exceptions and FastAPI exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class CertoError(Exception):
    """Base class for domain errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__doc__ or "Error"
        super().__init__(self.message)


class NotFoundError(CertoError):
    """Requested resource was not found."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(CertoError):
    """Resource conflicts with existing state."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(CertoError):
    """Input failed domain validation."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class ForbiddenError(CertoError):
    """Action not allowed in the current account state (e.g. email not verified)."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ExternalServiceError(CertoError):
    """An upstream service (E2B, judge, agent endpoint) failed."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "external_service_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CertoError)
    async def _handle_certo_error(_: Request, exc: CertoError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
