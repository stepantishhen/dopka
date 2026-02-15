import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps
import time

try:
    from zoneinfo import ZoneInfo
    _tz = ZoneInfo(os.environ.get("TZ", "Europe/Moscow"))
except Exception:
    _tz = None


class TZFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=_tz) if _tz else datetime.fromtimestamp(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(TZFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger("exam_system")


class LoggingService:
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "api_requests": [],
            "agent_calls": [],
            "errors": [],
            "total_requests": 0,
            "total_errors": 0
        }
    
    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        **kwargs
    ):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_time_ms": response_time * 1000,
            **kwargs
        }
        
        self.metrics["api_requests"].append(log_entry)
        self.metrics["total_requests"] += 1
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        logger.info(
            "API %s %s -> %s %.2fms%s",
            method,
            path,
            status_code,
            response_time * 1000,
            " " + extra if extra else "",
        )
        
        if len(self.metrics["api_requests"]) > 1000:
            self.metrics["api_requests"] = self.metrics["api_requests"][-1000:]
    
    def log_agent_call(
        self,
        agent_type: str,
        action: str,
        success: bool,
        response_time: float,
        **kwargs
    ):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": agent_type,
            "action": action,
            "success": success,
            "response_time_ms": response_time * 1000,
            **kwargs
        }
        
        self.metrics["agent_calls"].append(log_entry)
        logger.info(f"Agent Call: {agent_type}.{action} - {'Success' if success else 'Failed'} ({response_time*1000:.2f}ms)")
        
        if len(self.metrics["agent_calls"]) > 1000:
            self.metrics["agent_calls"] = self.metrics["agent_calls"][-1000:]
    
    def log_error(
        self,
        error_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "context": context or {}
        }
        
        self.metrics["errors"].append(log_entry)
        self.metrics["total_errors"] += 1
        logger.error(f"Error [{error_type}]: {message}", extra={"context": context})
        
        if len(self.metrics["errors"]) > 500:
            self.metrics["errors"] = self.metrics["errors"][-500:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        recent_requests = self.metrics["api_requests"][-100:] if self.metrics["api_requests"] else []
        recent_agent_calls = self.metrics["agent_calls"][-100:] if self.metrics["agent_calls"] else []
        recent_errors = self.metrics["errors"][-50:] if self.metrics["errors"] else []
        
        avg_response_time = 0.0
        if recent_requests:
            avg_response_time = sum(r.get("response_time_ms", 0) for r in recent_requests) / len(recent_requests)
        
        success_rate = 0.0
        if recent_agent_calls:
            success_count = sum(1 for c in recent_agent_calls if c.get("success", False))
            success_rate = success_count / len(recent_agent_calls)
        
        return {
            "total_requests": self.metrics["total_requests"],
            "total_errors": self.metrics["total_errors"],
            "avg_response_time_ms": avg_response_time,
            "agent_success_rate": success_rate,
            "recent_requests_count": len(recent_requests),
            "recent_agent_calls_count": len(recent_agent_calls),
            "recent_errors_count": len(recent_errors)
        }


logging_service = LoggingService()


def log_agent_call_decorator(agent_type: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, request, *args, **kwargs):
            start_time = time.time()
            try:
                result = await func(self, request, *args, **kwargs)
                response_time = time.time() - start_time
                
                logging_service.log_agent_call(
                    agent_type=agent_type,
                    action=request.action,
                    success=result.success,
                    response_time=response_time,
                    session_id=request.session_state.session_id if request.session_state else None
                )
                
                return result
            except Exception as e:
                response_time = time.time() - start_time
                logging_service.log_error(
                    error_type=f"{agent_type}_error",
                    message=str(e),
                    context={"action": request.action}
                )
                raise
        
        return wrapper
    return decorator
