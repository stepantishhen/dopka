import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services.logging_service import logging_service

logger = logging.getLogger("exam_system.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        path = request.url.path
        query = str(request.url.query) if request.url.query else None
        client = request.client.host if request.client else None
        logger.debug("request start %s %s query=%s client=%s", request.method, path, query, client)

        response = await call_next(request)
        response_time = time.time() - start_time

        logging_service.log_api_request(
            method=request.method,
            path=path,
            status_code=response.status_code,
            response_time=response_time,
            client_ip=client,
        )
        if response.status_code >= 400:
            logger.warning(
                "request error %s %s -> %s %.2fms client=%s",
                request.method,
                path,
                response.status_code,
                response_time * 1000,
                client,
            )
        return response
