import logging
import re
import json
from typing import Dict, List, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer

from backend.services.llm_client import LLMClient
import faiss
import numpy as np
import networkx as nx

from backend.models.didactic_unit import DidacticUnit

logger = logging.getLogger("exam_system.knowledge_service")


class KnowledgeService:
    def __init__(self):
        self.llm = LLMClient()
        self.embedding_model = SentenceTransformer(
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        )
        self.knowledge_base: Dict[str, DidacticUnit] = {}
        self.knowledge_graph = nx.DiGraph()
        self.content_index = faiss.IndexFlatIP(384)
        self.question_index = faiss.IndexFlatIP(384)
        self.content_db = []
        self.questions_db = []
    
    def safe_parse_json(self, text: str) -> Optional[Dict]:
        if not text or not isinstance(text, str):
            return None
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            patterns = [
                r'```json\s*(.*?)\s*```',
                r'```\s*(.*?)\s*```',
                r'JSON:\s*(\{.*\})',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    json_match = match
                    break
        
        if not json_match:
            return None
        
        json_text = json_match.group(1) if json_match and len(json_match.groups()) > 0 else (json_match.group() if json_match else text)
        
        try:
            json_text = json_text.replace('\ufeff', '').replace('\u200b', '')
            json_text = json_text.replace('"', '"').replace('"', '"')
            json_text = re.sub(r',\s*}', '}', json_text)
            json_text = re.sub(r',\s*]', ']', json_text)
            json_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_text)
            json_text = json_text.strip()
            if json_text.startswith('{') and not json_text.endswith('}'):
                json_text = json_text.rsplit('}', 1)[0] + '}'
            if json_text.startswith('[') and not json_text.endswith(']'):
                json_text = json_text.rsplit(']', 1)[0] + ']'
            return json.loads(json_text)
        except Exception as e:
            logger.debug("safe_parse_json error: %s", e)
            return None

    def extract_knowledge_from_text(self, text: str) -> List[DidacticUnit]:
        logger.info("extract_knowledge_from_text text_len=%s", len(text))
        if len(text) > 4000:
            text = text[:4000] + "... [текст сокращен]"
        system_prompt = "Ты эксперт-преподаватель, извлекающий дидактические единицы из текста. Извлекай ключевые концепции, определения, примеры и типичные ошибки."
        user_prompt = f"""Текст для анализа:
{text}

Извлеки дидактические единицы из текста. Формат ответа ТОЛЬКО JSON:
{{
    "units": [
        {{
            "unit_id": "unit_1",
            "title": "Название концепции",
            "content_type": "concept",
            "definition": "Определение концепции",
            "examples": ["Пример 1", "Пример 2"],
            "common_errors": ["Типичная ошибка 1"]
        }}
    ]
}}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.3, max_tokens=2000)
            
            data = self.safe_parse_json(response_text)
            
            if not data:
                return []
            
            units = []
            for unit_data in data.get("units", []):
                try:
                    unit_id = str(unit_data.get("unit_id", f"unit_{len(units)}"))
                    title = str(unit_data.get("title", "Без названия"))
                    content_type = str(unit_data.get("content_type", "concept"))
                    
                    unit = DidacticUnit(
                        unit_id=unit_id,
                        title=title,
                        content_type=content_type,
                        definition=str(unit_data.get("definition", "")),
                        examples=[str(ex) for ex in unit_data.get("examples", [])] if isinstance(unit_data.get("examples"), list) else [str(unit_data.get("examples", ""))],
                        common_errors=[str(err) for err in unit_data.get("common_errors", [])] if isinstance(unit_data.get("common_errors"), list) else [str(unit_data.get("common_errors", ""))]
                    )
                    
                    self.knowledge_base[unit.unit_id] = unit
                    self.knowledge_graph.add_node(unit.unit_id, title=unit.title, type=unit.content_type)
                    
                    content_text = f"{unit.title} {unit.definition} {' '.join(unit.examples)}"
                    emb = self.embedding_model.encode([content_text])
                    self.content_index.add(emb.astype('float32'))
                    self.content_db.append({
                        'unit_id': unit.unit_id,
                        'content': content_text
                    })
                    
                    units.append(unit)
                except Exception as e:
                    print(f"Ошибка при обработке единицы: {e}")
                    continue
            
            logger.info("extract_knowledge_from_text success units=%s", len(units))
            return units
        except Exception as e:
            logger.exception("extract_knowledge_from_text error: %s", e)
            return []

    def generate_questions_for_unit(self, unit_id: str, num_questions: int = 5) -> bool:
        logger.info("generate_questions_for_unit unit_id=%s num_questions=%s", unit_id, num_questions)
        if unit_id not in self.knowledge_base:
            logger.warning("generate_questions_for_unit unit not found unit_id=%s", unit_id)
            return False
        unit = self.knowledge_base[unit_id]
        
        system_prompt = "Ты эксперт-преподаватель, генерирующий вопросы для проверки знаний студентов."
        user_prompt = f"""Дидактическая единица: {unit.title}
Определение: {unit.definition}
Примеры: {json.dumps(unit.examples, ensure_ascii=False)}

Сгенерируй {num_questions} вопросов разных типов.

Формат ответа ТОЛЬКО JSON:
{{
    "questions": [
        {{
            "question": "Текст вопроса",
            "type": "understanding|application|analysis",
            "difficulty": 0.5,
            "criteria": [{{"name": "Критерий", "max_score": 2}}],
            "reference_answer": "Эталонный ответ"
        }}
    ]
}}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.5, max_tokens=2000)
            
            data = self.safe_parse_json(response_text)
            if data and "questions" in data:
                questions = data["questions"]
                if "understanding" not in unit.questions:
                    unit.questions["understanding"] = []
                if "application" not in unit.questions:
                    unit.questions["application"] = []
                if "analysis" not in unit.questions:
                    unit.questions["analysis"] = []
                
                for q in questions:
                    q_type = q.get("type", "understanding")
                    if q_type in unit.questions:
                        unit.questions[q_type].append(q)
                
                return True
            
            return False
        except Exception as e:
            print(f"Ошибка при генерации вопросов: {e}")
            return False
    
    def get_unit(self, unit_id: str) -> Optional[DidacticUnit]:
        return self.knowledge_base.get(unit_id)
    
    def get_all_units(self) -> List[DidacticUnit]:
        return list(self.knowledge_base.values())
