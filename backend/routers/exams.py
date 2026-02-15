import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from typing import List, Optional
import pdfplumber
import io

from backend.schemas.exams import (
    ExamCreate, ExamResponse, ExamSubmission, EvaluationResponse,
    CreateExamFromMaterialsRequest
)
from backend.services.exam_service import ExamService
from backend.models.exam_system import ExamConfig, StudentAnswer

logger = logging.getLogger("exam_system.exams")
router = APIRouter()


def get_exam_service(request: Request) -> ExamService:
    return request.app.state.exam_service


@router.post("/", response_model=ExamResponse)
async def create_exam(
    exam_data: ExamCreate,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.info("create_exam name=%s num_questions=%s adaptive=%s", exam_data.name, exam_data.num_questions, exam_data.adaptive)
    exam_config = ExamConfig(**exam_data.dict())
    exam = service.create_exam(exam_config)
    logger.info("create_exam success exam_id=%s join_code=%s", exam.exam_id, exam.join_code)
    return ExamResponse(**exam.dict())


@router.get("/current", response_model=Optional[ExamResponse])
async def get_current_exam(
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    exam = service.get_current_exam()
    if not exam:
        return None
    return ExamResponse(**exam.dict())


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: str,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.debug("get_exam exam_id=%s", exam_id)
    exam = service.get_exam(exam_id)
    if not exam:
        logger.warning("get_exam not found exam_id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Экзамен не найден")
    return ExamResponse(**exam.dict())


@router.post("/{exam_id}/submit", response_model=EvaluationResponse)
async def submit_exam(
    exam_id: str,
    submission: ExamSubmission,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.info("submit_exam exam_id=%s student_id=%s answers_count=%s", exam_id, submission.student_id, len(submission.answers))
    exam = service.get_exam(exam_id)
    if not exam:
        logger.warning("submit_exam exam not found exam_id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Экзамен не найден")
    answers = [StudentAnswer(**ans.dict()) for ans in submission.answers]
    evaluation = service.evaluate_student_answers(submission.student_id, answers)
    logger.info("submit_exam evaluated student_id=%s percentage=%.1f", submission.student_id, evaluation.get("percentage", 0))
    return EvaluationResponse(**evaluation)


@router.get("/join/{join_code}", response_model=ExamResponse)
async def get_exam_by_join_code(
    join_code: str,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.info("get_exam_by_join_code join_code=%s", join_code)
    exam = service.get_exam_by_join_code(join_code)
    if not exam:
        logger.warning("get_exam_by_join_code not found join_code=%s", join_code)
        raise HTTPException(status_code=404, detail="Экзамен с таким кодом не найден")
    return ExamResponse(**exam.dict())


@router.post("/create-sample", response_model=ExamResponse)
async def create_sample_exam(
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.info("create_sample_exam")
    exam = service.create_sample_exam()
    logger.info("create_sample_exam success exam_id=%s join_code=%s", exam.exam_id, exam.join_code)
    return ExamResponse(**exam.dict())


@router.get("/")
async def list_exams(
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    count = len(service.exams)
    logger.debug("list_exams count=%s", count)
    exams = [ExamResponse(**exam.dict()) for exam in service.exams.values()]
    return {"exams": exams, "count": count}


@router.post("/create-from-materials", response_model=ExamResponse)
async def create_exam_from_materials(
    request_data: CreateExamFromMaterialsRequest,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.info("create_exam_from_materials name=%s num_questions=%s has_text=%s unit_ids=%s",
                request_data.name, request_data.num_questions, bool(request_data.text), bool(request_data.unit_ids))
    knowledge_service = request.app.state.knowledge_service

    if request_data.text:
        units = knowledge_service.extract_knowledge_from_text(request_data.text)
        unit_ids = [unit.unit_id for unit in units]
    elif request_data.unit_ids:
        unit_ids = request_data.unit_ids
    else:

        unit_ids = list(knowledge_service.knowledge_base.keys())
    
    if not unit_ids:
        raise HTTPException(
            status_code=400,
            detail="Не найдено единиц знаний. Загрузите материалы или выберите единицы."
        )
    

    all_questions = []
    for unit_id in unit_ids[:20]:  
        unit = knowledge_service.get_unit(unit_id)
        if not unit:
            continue
        

        if not unit.questions or sum(len(qs) for qs in unit.questions.values()) == 0:
            knowledge_service.generate_questions_for_unit(
                unit_id,
                num_questions=request_data.questions_per_unit
            )
            unit = knowledge_service.get_unit(unit_id)  
        

        for q_type in ["understanding", "application", "analysis"]:
            if unit.questions.get(q_type):
                for q in unit.questions[q_type]:
                    q_with_unit = q.copy()
                    q_with_unit["unit_id"] = unit_id
                    all_questions.append(q_with_unit)
    
    if not all_questions:
        raise HTTPException(
            status_code=400,
            detail="Не удалось сгенерировать вопросы. Проверьте наличие материалов в базе знаний."
        )
    

    if len(all_questions) > request_data.num_questions:

        import random
        all_questions = random.sample(all_questions, request_data.num_questions)
    

    exam_config = ExamConfig(
        name=request_data.name,
        adaptive=request_data.adaptive,
        num_questions=len(all_questions),
        unit_ids=unit_ids
    )
    exam = service.create_exam(exam_config, questions=all_questions)
    logger.info("create_exam_from_materials success exam_id=%s questions=%s", exam.exam_id, len(all_questions))
    return ExamResponse(**exam.dict())


@router.post("/create-from-pdf", response_model=ExamResponse)
async def create_exam_from_pdf(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    num_questions: int = 10,
    adaptive: bool = True,
    questions_per_unit: int = 3,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    knowledge_service = request.app.state.knowledge_service
    logger.info("create_exam_from_pdf file=%s num_questions=%s", getattr(file, "filename", None), num_questions)
    try:
        contents = await file.read()
        logger.debug("create_exam_from_pdf read bytes=%s", len(contents))
        text = ""
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages[:20]:  
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Не удалось извлечь текст из PDF")
        

        units = knowledge_service.extract_knowledge_from_text(text)
        unit_ids = [unit.unit_id for unit in units]
        
        if not unit_ids:
            raise HTTPException(
                status_code=400,
                detail="Не удалось извлечь единицы знаний из PDF"
            )
        

        all_questions = []
        for unit_id in unit_ids[:20]:
            unit = knowledge_service.get_unit(unit_id)
            if not unit:
                continue
            
            if not unit.questions or sum(len(qs) for qs in unit.questions.values()) == 0:
                knowledge_service.generate_questions_for_unit(
                    unit_id,
                    num_questions=questions_per_unit
                )
                unit = knowledge_service.get_unit(unit_id)
            
            for q_type in ["understanding", "application", "analysis"]:
                if unit.questions.get(q_type):
                    for q in unit.questions[q_type]:
                        q_with_unit = q.copy()
                        q_with_unit["unit_id"] = unit_id
                        all_questions.append(q_with_unit)
        
        if not all_questions:
            raise HTTPException(
                status_code=400,
                detail="Не удалось сгенерировать вопросы"
            )
        

        if len(all_questions) > num_questions:
            import random
            all_questions = random.sample(all_questions, num_questions)
        

        exam_name = name or file.filename or "Экзамен из PDF"
        exam_config = ExamConfig(
            name=exam_name,
            adaptive=adaptive,
            num_questions=len(all_questions),
            unit_ids=unit_ids
        )
        exam = service.create_exam(exam_config, questions=all_questions)
        logger.info("create_exam_from_pdf success exam_id=%s questions=%s", exam.exam_id, len(all_questions))
        return ExamResponse(**exam.dict())
    except Exception as e:
        logger.exception("create_exam_from_pdf error: %s", e)
        raise HTTPException(status_code=400, detail=f"Ошибка при обработке PDF: {str(e)}")

