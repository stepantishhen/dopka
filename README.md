# DOPKA

Мульти-агентная система для проведения диалоговых экзаменов с виртуальным экзаменатором. Студенты отвечают на вопросы в чате, получают оценку и уточняющие подсказки; преподаватели создают экзамены из материалов и смотрят аналитику.

## Возможности

**Студенты**
- Прохождение экзамена в диалоговом режиме (вопрос → ответ → оценка / уточнение)
- Шкала: весь экзамен — 100 баллов суммарно по всем вопросам, порог сдачи — 56
- Баллы начисляются только за правильные ответы; при ошибке — уточняющий вопрос без добавления баллов
- Случайный порядок/варианты вопросов по дидактическим единицам
- Фиксированная левая панель: прогресс, текущий балл, подсказки
- Завершение экзамена и экран результатов без возврата к вопросам

**Преподаватели**
- Создание экзаменов из текста или PDF
- База знаний: дидактические единицы, извлечение из текста/PDF, генерация вопросов
- Список экзаменов, коды присоединения
- Аналитика по студентам и сессиям (`/api/teacher`)

## Стек

**Frontend:** React 18, React Router 6, Bootstrap 5, React Bootstrap, Vite

**Backend:** FastAPI, OpenAI-совместимый API (OpenAI, GigaChat и др.), Pydantic, SQLAlchemy (SQLite/PostgreSQL), при необходимости — sentence-transformers, FAISS, NetworkX

## Быстрый старт

### Docker Compose

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:3000  
- API Docs: http://localhost:8000/docs  

### Локально

**Backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Создайте в корне проекта или в `backend/` файл `.env`:

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./exam_system.db
SECRET_KEY=your-secret-key
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Запуск:

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**

```bash
npm install
npm run dev
```

По умолчанию фронт ожидает API на `http://localhost:8000/api` (или задайте `VITE_API_BASE_URL`).

## Архитектура

Оркестратор управляет сессией и вызывает агентов:

| Агент | Назначение |
|-------|------------|
| **Critic** | Оценка ответа (0–100 баллов за экзамен в сумме, доля на вопрос), is_correct, обратная связь |
| **Dialogue** | Уточняющие вопросы, переформулировка, подсказки при неверном ответе |
| **Planning** | Выбор следующего вопроса (адаптивно или по списку), случайный фактор среди топ-N |
| **Adaptive Exam** | Стратегия при пустом/слабом ответе (уровень упрощения, тактика) |
| **Analytics** | Запись метрик по сессии |
| **Knowledge** | База знаний, дидактические единицы (при использовании) |

Логика баллов:
- Экзамен = 100 баллов максимум; минимум для сдачи — 56.
- Агент оценивания получает номер вопроса, число вопросов и оставшийся бюджет, выставляет балл за текущий вопрос; бэкенд суммирует только оценки с `is_correct: true`.
- Контекст диалога: в LLM передаётся минимум 4 последних сообщения.

## API (основное)

**Оркестратор** `/api/orchestrator`
- `POST /sessions` — создание сессии (student_id, exam_id опционально)
- `GET /sessions/{session_id}` — статус сессии, при завершении — total_score, max_total_score, passed
- `POST /sessions/{session_id}/answer` — отправить ответ (question_id, answer, question_data)
- `POST /sessions/{session_id}/next-question` — следующий вопрос (exam_config)
- `POST /sessions/{session_id}/complete` — завершить экзамен
- `GET /sessions/{session_id}/dialogue` — история диалога

**Экзамены** `/api/exams`
- `GET /` — список экзаменов
- `GET /{exam_id}` — экзамен по ID
- `GET /join/{join_code}` — экзамен по коду входа
- `POST /create-from-materials` — экзамен из текста (name, text или unit_ids, num_questions, adaptive, questions_per_unit)
- `POST /create-from-pdf` — экзамен из PDF

**Аутентификация** `/api/auth`
- `POST /register`, `POST /login` — регистрация и вход (email, password, name, role)

**Преподаватель** `/api/teacher` (требуется роль преподавателя)
- `GET /students` — студенты с аналитикой
- `GET /students/{student_id}/analytics` — аналитика по студенту

**База знаний** `/api/knowledge-base`
- Элементы, извлечение из текста/PDF, генерация вопросов по единице

## Структура проекта

```
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/          # session, exam, didactic_unit, user, analytics
│   ├── schemas/
│   ├── routers/         # orchestrator, exams, auth, teacher, knowledge_base, chat, students
│   ├── services/
│   │   ├── orchestrator.py
│   │   ├── exam_service.py
│   │   ├── knowledge_service.py
│   │   ├── chat_service.py
│   │   ├── llm_client.py
│   │   └── agents/      # critic, dialogue, planning, adaptive_exam, analytics, knowledge
│   ├── repositories/
│   └── middleware/
├── src/
│   ├── components/      # ExamSession, ChatDialog, Navigation, Analytics, ProtectedRoute
│   ├── pages/           # Home, Login, JoinExam, Exams, KnowledgeBase, Profile, History
│   ├── context/         # AuthContext, ExamSessionContext, ChatContext
│   └── services/        # api
├── index.html
├── package.json
├── vite.config.js
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```

## Лицензия

MIT
