import re
import json
from typing import Dict, List, Optional
from datetime import datetime
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import networkx as nx

from backend.models.didactic_unit import DidacticUnit
from backend.config import settings


class KnowledgeService:
    def __init__(self):
        self.giga = GigaChat(credentials=settings.gigachat_credentials, verify_ssl_certs=False)
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
            return json.loads(json_text)
        except Exception as e:
            print(f"JSON parsing error: {e}")
            return None
    
    def extract_knowledge_from_text(self, text: str) -> List[DidacticUnit]:
        if len(text) > 4000:
            text = text[:4000] + "... [текст сокращен]"
        
        system_prompt = """Ты - эксперт по дидактике. Извлеки дидактические единицы из текста.
        Ответ должен быть ТОЛЬКО в формате JSON."""
        
        user_prompt = f"""
        Анализируй следующий текст и выдели дидактические единицы:
        
        ТЕКСТ:
        {text}
        
        Для каждой единицы определи:
        1. unit_id: уникальный ID (латинские буквы и цифры)
        2. title: четкое название (на русском)
        3. definition: определение (1-2 предложения)
        4. examples: 1-2 примера (массив строк)
        5. common_errors: 1-2 типичные ошибки (массив строк)
        6. content_type: тип (concept, skill, definition, example)
        
        Формат ответа ТОЛЬКО JSON:
        {{
            "units": [
                {{
                    "unit_id": "python_var_01",
                    "title": "Переменная в Python",
                    "definition": "...",
                    "examples": ["x = 10"],
                    "common_errors": ["..."],
                    "content_type": "concept"
                }}
            ]
        }}
        """
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.3, max_tokens=2000)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
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
            
            return units
        except Exception as e:
            print(f"Ошибка при извлечении знаний: {e}")
            return []
    
    def generate_questions_for_unit(self, unit_id: str, num_questions: int = 5) -> bool:
        if unit_id not in self.knowledge_base:
            return False
        
        unit = self.knowledge_base[unit_id]
        
        system_prompt = """Ты - опытный преподаватель. Сгенерируй разнообразные вопросы."""
        
        user_prompt = f"""
        Дидактическая единица: {unit.title}
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
        }}
        """
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.7, max_tokens=2000)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            data = self.safe_parse_json(response_text)
            
            if not data:
                return False
            
            for q_data in data.get("questions", []):
                question_obj = {
                    "question_id": f"q_{len(self.questions_db)}",
                    "question": q_data["question"],
                    "type": q_data["type"],
                    "difficulty": q_data.get("difficulty", 0.5),
                    "unit_id": unit_id,
                    "criteria": q_data.get("criteria", []),
                    "reference_answer": q_data.get("reference_answer", "")
                }
                
                q_type = q_data["type"]
                if q_type in unit.questions:
                    unit.questions[q_type].append(question_obj)
                
                emb = self.embedding_model.encode([q_data["question"]])
                self.question_index.add(emb.astype('float32'))
                self.questions_db.append(question_obj)
            
            unit.metadata["updated_at"] = datetime.now().isoformat()
            return True
        except Exception as e:
            print(f"Ошибка при генерации вопросов: {e}")
            return False
    
    def get_all_units(self) -> List[Dict]:
        return [unit.model_dump() for unit in self.knowledge_base.values()]
    
    def get_unit(self, unit_id: str) -> Optional[DidacticUnit]:
        return self.knowledge_base.get(unit_id)
    
    def add_unit(self, unit: DidacticUnit):
        self.knowledge_base[unit.unit_id] = unit
        self.knowledge_graph.add_node(unit.unit_id, title=unit.title, type=unit.content_type)

