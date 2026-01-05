from typing import Dict, Any
from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType
from backend.services.knowledge_service import KnowledgeService


class KnowledgeAgent(BaseAgent):
    def __init__(self, knowledge_service):
        super().__init__(AgentType.KNOWLEDGE)
        self.knowledge_service = knowledge_service
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        action = request.action
        context = request.context
        
        try:
            if action == "get_unit":
                unit_id = context.get("unit_id")
                if unit_id:
                    unit = self.knowledge_service.get_unit(unit_id)
                    if unit:
                        return self._create_response(
                            True,
                            {"unit": unit.model_dump()}
                        )
                    return self._create_response(False, error="Unit not found")
            
            elif action == "get_all_units":
                units = self.knowledge_service.get_all_units()
                return self._create_response(True, {"units": units})
            
            elif action == "search_similar":
                query = context.get("query")
                top_k = context.get("top_k", 5)
                if query:

                    query_emb = self.knowledge_service.embedding_model.encode([query])
                    if self.knowledge_service.content_index.ntotal > 0:
                        distances, indices = self.knowledge_service.content_index.search(
                            query_emb.astype('float32'), top_k
                        )
                        results = []
                        for idx, dist in zip(indices[0], distances[0]):
                            if idx < len(self.knowledge_service.content_db):
                                results.append({
                                    **self.knowledge_service.content_db[idx],
                                    "similarity": float(dist)
                                })
                        return self._create_response(True, {"results": results})
                    return self._create_response(True, {"results": []})
            
            elif action == "extract_from_text":
                text = context.get("text")
                if text:
                    units = self.knowledge_service.extract_knowledge_from_text(text)
                    return self._create_response(
                        True,
                        {"units": [u.model_dump() for u in units]}
                    )
            
            elif action == "generate_questions":
                unit_id = context.get("unit_id")
                num_questions = context.get("num_questions", 5)
                if unit_id:
                    success = self.knowledge_service.generate_questions_for_unit(
                        unit_id, num_questions
                    )
                    return self._create_response(success, {"unit_id": unit_id})
            
            return self._create_response(False, error=f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_response(False, error=str(e))

