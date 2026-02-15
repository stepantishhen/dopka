import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from typing import List, Optional
import pdfplumber
import io

from backend.schemas.knowledge_base import (
    KnowledgeItemCreate, KnowledgeItemResponse, KnowledgeItemUpdate,
    DidacticUnitCreate, DidacticUnitResponse
)
from pydantic import BaseModel
from backend.services.knowledge_service import KnowledgeService

logger = logging.getLogger("exam_system.knowledge_base")
router = APIRouter()


def get_knowledge_service(request: Request) -> KnowledgeService:
    return request.app.state.knowledge_service


@router.get("/items", response_model=List[KnowledgeItemResponse])
async def get_knowledge_items(
    search: Optional[str] = None,
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    logger.debug("get_knowledge_items search=%s", search)
    units = service.get_all_units()
    items = []
    for unit in units:
        items.append(KnowledgeItemResponse(
            id=unit["unit_id"],
            title=unit["title"],
            content=unit["definition"],
            category=unit.get("content_type", ""),
            tags=unit.get("common_errors", []),
            createdAt=unit["metadata"]["created_at"],
            updatedAt=unit["metadata"]["updated_at"]
        ))
    
    if search:
        search_lower = search.lower()
        items = [item for item in items if 
                search_lower in item.title.lower() or 
                search_lower in item.content.lower() or
                any(search_lower in tag.lower() for tag in item.tags)]
    logger.debug("get_knowledge_items result count=%s", len(items))
    return items


@router.post("/items", response_model=KnowledgeItemResponse)
async def create_knowledge_item(
    item: KnowledgeItemCreate,
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    from backend.models.didactic_unit import DidacticUnit
    from datetime import datetime
    logger.info("create_knowledge_item title=%s category=%s", item.title, item.category)
    unit_id = f"unit_{datetime.now().timestamp()}"
    unit = DidacticUnit(
        unit_id=unit_id,
        title=item.title,
        content_type=item.category or "concept",
        definition=item.content,
        examples=[],
        common_errors=item.tags
    )
    
    service.add_unit(unit)
    logger.info("create_knowledge_item success unit_id=%s", unit_id)
    return KnowledgeItemResponse(
        id=unit.unit_id,
        title=unit.title,
        content=unit.definition,
        category=unit.content_type,
        tags=unit.common_errors,
        createdAt=unit.metadata["created_at"],
        updatedAt=unit.metadata["updated_at"]
    )


@router.put("/items/{item_id}", response_model=KnowledgeItemResponse)
async def update_knowledge_item(
    item_id: str,
    item: KnowledgeItemUpdate,
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    logger.info("update_knowledge_item item_id=%s", item_id)
    unit = service.get_unit(item_id)
    if not unit:
        logger.warning("update_knowledge_item not found item_id=%s", item_id)
        raise HTTPException(status_code=404, detail="Элемент не найден")
    
    from datetime import datetime
    
    if item.title is not None:
        unit.title = item.title
    if item.content is not None:
        unit.definition = item.content
    if item.category is not None:
        unit.content_type = item.category
    if item.tags is not None:
        unit.common_errors = item.tags
    
    unit.metadata["updated_at"] = datetime.now().isoformat()
    
    return KnowledgeItemResponse(
        id=unit.unit_id,
        title=unit.title,
        content=unit.definition,
        category=unit.content_type,
        tags=unit.common_errors,
        createdAt=unit.metadata["created_at"],
        updatedAt=unit.metadata["updated_at"]
    )


@router.delete("/items/{item_id}")
async def delete_knowledge_item(
    item_id: str,
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    logger.info("delete_knowledge_item item_id=%s", item_id)
    if item_id not in service.knowledge_base:
        logger.warning("delete_knowledge_item not found item_id=%s", item_id)
        raise HTTPException(status_code=404, detail="Элемент не найден")
    del service.knowledge_base[item_id]
    return {"message": "Элемент удален"}


class TextExtractRequest(BaseModel):
    text: str


@router.post("/extract-from-text")
async def extract_from_text(
    request_data: TextExtractRequest,
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    logger.info("extract_from_text text_len=%s", len(request_data.text or ""))
    units = service.extract_knowledge_from_text(request_data.text)
    logger.info("extract_from_text success units_count=%s", len(units))
    return {"units": [unit.model_dump() for unit in units], "count": len(units)}


@router.post("/extract-from-pdf")
async def extract_from_pdf(
    file: UploadFile = File(...),
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    logger.info("extract_from_pdf file=%s", getattr(file, "filename", None))
    try:
        contents = await file.read()
        logger.debug("extract_from_pdf read bytes=%s", len(contents))
        text = ""
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for i, page in enumerate(pdf.pages[:10]):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        units = service.extract_knowledge_from_text(text)
        logger.info("extract_from_pdf success units_count=%s", len(units))
        return {"units": [unit.model_dump() for unit in units], "count": len(units)}
    except Exception as e:
        logger.exception("extract_from_pdf error: %s", e)
        raise HTTPException(status_code=400, detail=f"Ошибка при обработке PDF: {str(e)}")


@router.post("/units/{unit_id}/generate-questions")
async def generate_questions(
    unit_id: str,
    num_questions: int = 5,
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    logger.info("generate_questions unit_id=%s num_questions=%s", unit_id, num_questions)
    success = service.generate_questions_for_unit(unit_id, num_questions)
    if not success:
        logger.warning("generate_questions failed unit_id=%s", unit_id)
        raise HTTPException(status_code=404, detail="Единица не найдена или ошибка генерации")
    
    unit = service.get_unit(unit_id)
    return {
        "message": "Вопросы сгенерированы",
        "questions": unit.questions if unit else {}
    }


@router.get("/units", response_model=List[DidacticUnitResponse])
async def get_didactic_units(
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    units = service.get_all_units()
    return [DidacticUnitResponse(**unit) for unit in units]


@router.get("/units/{unit_id}", response_model=DidacticUnitResponse)
async def get_didactic_unit(
    unit_id: str,
    request: Request = None,
    service: KnowledgeService = Depends(get_knowledge_service)
):
    unit = service.get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Единица не найдена")
    return DidacticUnitResponse(**unit.model_dump())

