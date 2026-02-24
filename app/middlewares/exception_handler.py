from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from app.models.schemas import APIResponse

logger = logging.getLogger(__name__)


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.exception("Unhandled exception")
            body = APIResponse(success=False, message="Internal server error", data=None, errors=[str(exc)])
            return JSONResponse(status_code=500, content=body.dict())
