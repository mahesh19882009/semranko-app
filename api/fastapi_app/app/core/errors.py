import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_code: int, message: str, data=None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.data = data


def _cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin")
    settings = get_settings()
    allowed = [settings.FRONTEND_URL] if settings.FRONTEND_URL else []
    if not allowed:
        return {}
    if "*" in allowed or origin in allowed:
        return {
            "access-control-allow-origin": origin or "*",
            "access-control-allow-credentials": "true",
            "access-control-allow-methods": "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT",
        }
    return {}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=_cors_headers(request),
            content={
                "success": False,
                "message": exc.message,
                "data": exc.data,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            headers=_cors_headers(request),
            content={"success": False, "message": "Internal server error"},
        )