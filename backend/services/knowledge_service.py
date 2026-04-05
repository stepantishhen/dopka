import logging
import re
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.services.llm_client import LLMClient
from backend.schemas.structured_outputs import ExtractKnowledgeStructured, GenerateQuestionsStructured
import faiss
import numpy as np
import networkx as nx

from backend.models.didactic_unit import DidacticUnit
from backend.config import settings

logger = logging.getLogger("exam_system.knowledge_service")

# Должно совпадать с выходной размерностью выбранной модели (paraphrase-MiniLM-L3-v2 и multilingual-MiniLM-L12 — 384)
_EMBEDDING_DIM = 384

# Длинный JSON от LLM обрезается по max_tokens → невалидный JSON; поднимаем потолок и режем вход по чанкам.
EXTRACT_MAX_OUTPUT_TOKENS = 16384
EXTRACT_SINGLE_INPUT_MAX = 12000
EXTRACT_CHUNK_THRESHOLD = 9000
EXTRACT_CHUNK_SIZE = 6500
EXTRACT_CHUNK_STEP = 5200  # перекрытие ~1300 символов между чанками


class KnowledgeService:
    def __init__(self):
        self.llm = LLMClient()
        # Не загружаем при старте: скачивание с Hugging Face блокирует поднятие API на несколько минут.
        self._embedding_model = None
        self.knowledge_base: Dict[str, DidacticUnit] = {}
        self.knowledge_graph = nx.DiGraph()
        self.content_index = faiss.IndexFlatIP(_EMBEDDING_DIM)
        self.question_index = faiss.IndexFlatIP(_EMBEDDING_DIM)
        self.content_db = []
        self.questions_db = []

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            name = settings.embedding_model_name
            logger.info(
                "Загрузка модели эмбеддингов: %s (первый запуск — скачивание с Hugging Face, для L3 ~60 МБ)...",
                name,
            )
            self._embedding_model = SentenceTransformer(name)
            logger.info("Модель эмбеддингов готова")
        return self._embedding_model

    def add_unit(self, unit: DidacticUnit) -> None:
        """Добавляет дидактическую единицу в базу и индекс для поиска."""
        self.knowledge_base[unit.unit_id] = unit
        self.knowledge_graph.add_node(unit.unit_id, title=unit.title, type=unit.content_type)
        content_text = f"{unit.title} {unit.definition} {' '.join(unit.examples)}"
        emb = self.embedding_model.encode([content_text])
        self.content_index.add(emb.astype("float32"))
        self.content_db.append({"unit_id": unit.unit_id, "content": content_text})
        logger.info("add_unit unit_id=%s", unit.unit_id)

    def register_unit_without_embeddings(self, unit: DidacticUnit) -> None:
        """
        Только словарь + граф знаний, без SentenceTransformer и FAISS.
        Для сида/демо и быстрого старта API; семантический поиск по этим единицам недоступен до add_unit/extract.
        """
        self.knowledge_base[unit.unit_id] = unit
        self.knowledge_graph.add_node(unit.unit_id, title=unit.title, type=unit.content_type)
        logger.info("register_unit_without_embeddings unit_id=%s", unit.unit_id)

    def find_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Ищет вопрос по идентификатору во всех единицах базы знаний."""
        for unit in self.knowledge_base.values():
            for _qtype, qs in (unit.questions or {}).items():
                if not isinstance(qs, list):
                    continue
                for q in qs:
                    if isinstance(q, dict) and q.get("question_id") == question_id:
                        return q
        return None
    
    def safe_parse_json(self, text: str) -> Optional[Dict]:
        if not text or not isinstance(text, str):
            return None

        candidates: List[str] = []

        # 1) Закрытый блок ```json ... ```
        m = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if m:
            candidates.append(m.group(1).strip())

        # 2) Открытый ```json без закрытия (ответ обрезан провайдером)
        if not candidates:
            m = re.search(r"```json\s*([\s\S]*)$", text, re.IGNORECASE)
            if m:
                candidates.append(m.group(1).strip())

        # 3) Общий fenced block
        if not candidates:
            m = re.search(r"```\s*([\s\S]*?)\s*```", text)
            if m:
                candidates.append(m.group(1).strip())

        # 4) Самый внешний объект { ... }
        if not candidates:
            m = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
            if m:
                candidates.append(m.group(0).strip())

        for json_text in candidates:
            parsed = self._try_load_json_object(json_text)
            if parsed is not None:
                return parsed
        return None

    def _try_load_json_object(self, json_text: str) -> Optional[Dict]:
        if not json_text:
            return None
        try:
            json_text = json_text.replace("\ufeff", "").replace("\u200b", "")
            json_text = json_text.replace("\u201c", '"').replace("\u201d", '"')
            json_text = re.sub(r",\s*}", "}", json_text)
            json_text = re.sub(r",\s*]", "]", json_text)
            json_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_text)
            json_text = json_text.strip()
            if json_text.startswith("{") and not json_text.endswith("}"):
                # Обрезанный JSON: последняя закрывающая скобка объекта
                idx = json_text.rfind("}")
                if idx > 1:
                    json_text = json_text[: idx + 1]
            if json_text.startswith("[") and not json_text.endswith("]"):
                idx = json_text.rfind("]")
                if idx > 1:
                    json_text = json_text[: idx + 1]
            out = json.loads(json_text)
            return out if isinstance(out, dict) else None
        except json.JSONDecodeError as e:
            logger.debug("JSONDecodeError: %s (len=%s)", e, len(json_text))
            return None
        except Exception as e:
            logger.debug("safe_parse_json inner error: %s", e)
            return None

    def _process_extracted_unit_dicts(self, unit_rows: List[Dict], response_fragment: str = "") -> List[DidacticUnit]:
        """Добавляет единицы в граф/индекс и возвращает список успешно созданных DidacticUnit."""
        units: List[DidacticUnit] = []
        for unit_data in unit_rows:
            if not isinstance(unit_data, dict):
                continue
            try:
                unit_id = str(unit_data.get("unit_id", f"unit_{len(units)}") or f"unit_{len(units)}")
                title = str(unit_data.get("title", "Без названия"))
                content_type = str(unit_data.get("content_type", "concept"))

                unit = DidacticUnit(
                    unit_id=unit_id,
                    title=title,
                    content_type=content_type,
                    definition=str(unit_data.get("definition", "")),
                    examples=[str(ex) for ex in unit_data.get("examples", [])]
                    if isinstance(unit_data.get("examples"), list)
                    else [str(unit_data.get("examples", ""))],
                    common_errors=[str(err) for err in unit_data.get("common_errors", [])]
                    if isinstance(unit_data.get("common_errors"), list)
                    else [str(unit_data.get("common_errors", ""))],
                )

                self.knowledge_base[unit.unit_id] = unit
                self.knowledge_graph.add_node(unit.unit_id, title=unit.title, type=unit.content_type)

                content_text = f"{unit.title} {unit.definition} {' '.join(unit.examples)}"
                emb = self.embedding_model.encode([content_text])
                self.content_index.add(emb.astype("float32"))
                self.content_db.append({"unit_id": unit.unit_id, "content": content_text})

                units.append(unit)
            except Exception as e:
                logger.warning("Ошибка при обработке единицы: %s", e)
                continue

        if not units and unit_rows:
            logger.warning(
                "extract_knowledge_from_text: не удалось сохранить ни одной единицы (rows=%s). Фрагмент: %s",
                len(unit_rows),
                response_fragment[:400] if response_fragment else "",
            )
        return units

    def _legacy_unit_rows(self, text: str) -> List[Dict]:
        """Свободный JSON + safe_parse_json — только список словарей единиц."""
        system_prompt = "Ты эксперт-преподаватель, извлекающий дидактические единицы из текста. Извлекай ключевые концепции, определения, примеры и типичные ошибки. Отвечай одним JSON-объектом с ключом units, без markdown, если просят иначе — всё равно валидный JSON."
        user_prompt = f"""Текст для анализа:
{text}

Извлеки дидактические единицы. Формат ответа — только JSON:
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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response_text = self.llm.chat(messages, temperature=0.3, max_tokens=EXTRACT_MAX_OUTPUT_TOKENS)
        data = self.safe_parse_json(response_text or "")
        if not data:
            logger.warning(
                "extract_knowledge_from_text (legacy): ответ LLM не распознан как JSON (первые 800 символов): %s",
                (response_text or "")[:800],
            )
            return []
        rows = data.get("units", [])
        return rows if isinstance(rows, list) else []

    def _extract_unit_rows_structured_then_legacy(self, text: str, chunk_preamble: str = "") -> List[Dict]:
        """Structured output, при ошибке — legacy. Возвращает списки полей units без записи в граф."""
        system_prompt = (
            "Ты эксперт-преподаватель, извлекающий дидактические единицы из текста. "
            "Извлекай ключевые концепции, определения, примеры и типичные ошибки. "
            "Ответ строго по заданной схеме (structured output)."
        )
        preamble = (chunk_preamble + "\n\n") if chunk_preamble else ""
        user_prompt = f"""{preamble}Текст для анализа:
{text}

Извлеки все релевантные дидактические единицы. Заполни поля unit_id, title, content_type, definition, examples, common_errors."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            parsed = self.llm.chat_structured(
                messages,
                ExtractKnowledgeStructured,
                temperature=0.3,
                max_tokens=EXTRACT_MAX_OUTPUT_TOKENS,
            )
            return [u.model_dump() for u in parsed.units]
        except Exception as e:
            logger.warning(
                "extract_knowledge_from_text: structured output ошибка (%s), fallback на свободный JSON",
                e,
            )
            return self._legacy_unit_rows(text)

    def _extract_knowledge_chunked(self, full_text: str) -> List[DidacticUnit]:
        """Длинный PDF/текст: несколько запросов с перекрытием, дедупликация по названию."""
        merged: List[Dict] = []
        seen_titles: set = set()
        offset = 0
        while offset < len(full_text):
            chunk = full_text[offset : offset + EXTRACT_CHUNK_SIZE]
            if len(chunk) < 400:
                break
            preamble = (
                f"Это фрагмент большого документа (символы {offset}–{offset + len(chunk)}). "
                f"Извлеки единицы только из этого фрагмента; unit_id нумеруй unit_1, unit_2, … внутри фрагмента."
            )
            logger.info("extract_knowledge_chunked offset=%s chunk_len=%s", offset, len(chunk))
            rows = self._extract_unit_rows_structured_then_legacy(chunk, chunk_preamble=preamble)
            for r in rows:
                if not isinstance(r, dict):
                    continue
                title_key = (r.get("title") or "").strip().lower()[:400]
                if not title_key:
                    continue
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                merged.append(r)
            offset += EXTRACT_CHUNK_STEP
        for i, r in enumerate(merged):
            if isinstance(r, dict):
                r["unit_id"] = f"u_{i + 1}_{uuid.uuid4().hex[:8]}"
        units = self._process_extracted_unit_dicts(merged)
        logger.info("extract_knowledge_chunked total_units=%s", len(units))
        return units

    def _extract_knowledge_legacy(self, text: str) -> List[DidacticUnit]:
        """Резервный путь целиком (совместимость): legacy JSON → граф."""
        rows = self._legacy_unit_rows(text)
        return self._process_extracted_unit_dicts(rows, response_fragment="legacy")

    def extract_knowledge_from_text(self, text: str) -> List[DidacticUnit]:
        text = (text or "").strip()
        if not text:
            return []
        logger.info("extract_knowledge_from_text text_len=%s", len(text))
        if len(text) > EXTRACT_CHUNK_THRESHOLD:
            return self._extract_knowledge_chunked(text)

        trimmed = text[:EXTRACT_SINGLE_INPUT_MAX] + ("..." if len(text) > EXTRACT_SINGLE_INPUT_MAX else "")
        rows = self._extract_unit_rows_structured_then_legacy(trimmed)
        units = self._process_extracted_unit_dicts(rows)
        logger.info("extract_knowledge_from_text success units=%s", len(units))
        return units

    def _append_questions_from_dicts(self, unit: DidacticUnit, unit_id: str, questions: List[Dict]) -> int:
        """Добавляет вопросы из списка словарей в unit.questions по типу. Возвращает число добавленных."""
        if "understanding" not in unit.questions:
            unit.questions["understanding"] = []
        if "application" not in unit.questions:
            unit.questions["application"] = []
        if "analysis" not in unit.questions:
            unit.questions["analysis"] = []

        appended = 0
        for q in questions:
            if not isinstance(q, dict):
                continue
            q_text = q.get("question") or q.get("text") or q.get("content")
            if q_text:
                q["question"] = str(q_text)
            if not q.get("question"):
                continue
            raw_type = str(q.get("type", "understanding")).lower().strip()
            if raw_type not in ("understanding", "application", "analysis"):
                raw_type = "understanding"
            q_type = raw_type
            if not q.get("question_id"):
                q["question_id"] = f"{unit_id}_q_{uuid.uuid4().hex[:12]}"
            unit.questions[q_type].append(q)
            appended += 1
        return appended

    def _generate_questions_legacy(self, unit_id: str, unit: DidacticUnit, num_questions: int) -> bool:
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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response_text = self.llm.chat(messages, temperature=0.5, max_tokens=2000)
        data = self.safe_parse_json(response_text)
        if not data or "questions" not in data:
            logger.warning(
                "generate_questions_for_unit (legacy) unit_id=%s: нет JSON с ключом questions. Ответ: %s",
                unit_id,
                (response_text or "")[:500],
            )
            return False
        questions = data["questions"]
        if not questions:
            logger.warning("generate_questions_for_unit (legacy) unit_id=%s: пустой список questions", unit_id)
            return False
        appended = self._append_questions_from_dicts(unit, unit_id, questions)
        if appended == 0:
            logger.warning("generate_questions_for_unit (legacy) unit_id=%s: ни одного вопроса не добавлено", unit_id)
            return False
        logger.info("generate_questions_for_unit legacy unit_id=%s appended=%s", unit_id, appended)
        return True

    def generate_questions_for_unit(self, unit_id: str, num_questions: int = 5) -> bool:
        logger.info("generate_questions_for_unit unit_id=%s num_questions=%s", unit_id, num_questions)
        if unit_id not in self.knowledge_base:
            logger.warning("generate_questions_for_unit unit not found unit_id=%s", unit_id)
            return False
        unit = self.knowledge_base[unit_id]

        system_prompt = (
            "Ты эксперт-преподаватель, генерирующий вопросы для проверки знаний студентов. "
            "Ответ строго по заданной схеме (structured output)."
        )
        user_prompt = f"""Дидактическая единица: {unit.title}
Определение: {unit.definition}
Примеры: {json.dumps(unit.examples, ensure_ascii=False)}

Сгенерируй ровно {num_questions} вопросов разных типов (understanding, application, analysis).
Для каждого вопроса укажи question, type, difficulty (0–1), criteria (name, max_score), reference_answer."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            parsed = self.llm.chat_structured(
                messages,
                GenerateQuestionsStructured,
                temperature=0.5,
                max_tokens=4000,
            )
            qdicts = [q.model_dump() for q in parsed.questions]
            appended = self._append_questions_from_dicts(unit, unit_id, qdicts)
            if appended == 0:
                logger.warning("generate_questions_for_unit unit_id=%s: structured не дал вопросов", unit_id)
                return self._generate_questions_legacy(unit_id, unit, num_questions)
            logger.info("generate_questions_for_unit structured unit_id=%s appended=%s", unit_id, appended)
            return True
        except Exception as e:
            logger.warning(
                "generate_questions_for_unit unit_id=%s: structured output недоступен (%s), fallback",
                unit_id,
                e,
            )
            try:
                return self._generate_questions_legacy(unit_id, unit, num_questions)
            except Exception as e2:
                logger.exception("generate_questions_for_unit unit_id=%s error: %s", unit_id, e2)
                return False
    
    def get_unit(self, unit_id: str) -> Optional[DidacticUnit]:
        return self.knowledge_base.get(unit_id)
    
    def get_all_units(self) -> List[DidacticUnit]:
        return list(self.knowledge_base.values())
