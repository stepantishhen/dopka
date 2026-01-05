import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from backend.services.logging_service import logging_service


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        response_time = time.time() - start_time
        
        logging_service.log_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time=response_time,
            client_ip=request.client.host if request.client else None
        )
        
        return response
