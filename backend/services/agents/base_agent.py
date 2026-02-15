from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.models.session import AgentRequest, AgentResponse, AgentType


class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.metrics: Dict[str, Any] = {
            "requests_count": 0,
            "success_count": 0,
            "error_count": 0,
            "avg_response_time": 0.0
        }
    
    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        pass
    
    def _create_response(
        self,
        success: bool,
        data: Dict[str, Any] = None,
        error: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> AgentResponse:
        self.metrics["requests_count"] += 1
        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["error_count"] += 1
        
        return AgentResponse(
            success=success,
            data=data or {},
            error=error,
            metadata=metadata or {}
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics.copy()

