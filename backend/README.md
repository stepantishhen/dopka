# Backend API - Система обучения с виртуальным экзаменатором

FastAPI backend для системы обучения студентов и преподавателей.

## Требования

- Python 3.11 или 3.12 (не рекомендуется Python 3.14, так как библиотека `gigachat` использует Pydantic v1, которая несовместима с Python 3.14)

## Установка

### Локальная установка

1. Убедитесь, что используете Python 3.11 или 3.12:
```bash
python --version
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

5. Настройте переменные окружения в `.env`:
```env
GIGACHAT_CREDENTIALS=your_credentials_here
DATABASE_URL=sqlite:///./exam_system.db
SECRET_KEY=your-secret-key-here
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

6. Запустите сервер:
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend будет доступен на `http://localhost:8000`
API документация: `http://localhost:8000/docs`

### Docker

#### Production
```bash
docker-compose up backend
```

#### Development (с hot-reload)
```bash
docker-compose -f ../docker-compose.dev.yml up backend
```

## Структура проекта

```
backend/
├── main.py                 # Точка входа FastAPI приложения
├── config.py              # Конфигурация и настройки
├── requirements.txt       # Зависимости Python
├── models/                # Модели данных (Pydantic)
│   ├── didactic_unit.py
│   └── exam_system.py
├── schemas/               # Схемы для API (request/response)
│   ├── knowledge_base.py
│   ├── exams.py
│   ├── students.py
│   └── chat.py
├── services/              # Бизнес-логика
│   ├── knowledge_service.py
│   ├── exam_service.py
│   └── chat_service.py
└── routers/               # API роутеры
    ├── knowledge_base.py
    ├── exams.py
    ├── students.py
    └── chat.py
```

## API Endpoints

### База знаний (`/api/knowledge-base`)
- `GET /items` - Получить все элементы
- `POST /items` - Создать элемент
- `PUT /items/{item_id}` - Обновить элемент
- `DELETE /items/{item_id}` - Удалить элемент
- `POST /extract-from-text` - Извлечь единицы из текста
- `POST /extract-from-pdf` - Извлечь единицы из PDF
- `POST /units/{unit_id}/generate-questions` - Сгенерировать вопросы

### Экзамены (`/api/exams`)
- `GET /` - Список экзаменов
- `POST /` - Создать экзамен
- `GET /current` - Текущий активный экзамен
- `GET /{exam_id}` - Получить экзамен
- `POST /{exam_id}/submit` - Отправить ответы

### Студенты (`/api/students`)
- `GET /` - Список студентов
- `POST /` - Создать профиль
- `GET /{student_id}` - Профиль студента
- `POST /{student_id}/emotional-state` - Оценить эмоциональное состояние
- `POST /{student_id}/diagnostic` - Диагностика знаний

### Чат (`/api/chat`)
- `GET /` - Список чатов
- `POST /` - Создать чат
- `GET /{chat_id}` - Получить чат
- `POST /{chat_id}/message` - Отправить сообщение

## Интеграция с фронтендом

Backend настроен для работы с React фронтендом на `http://localhost:3000` или `http://localhost:5173`.

CORS настроен в `main.py` для разрешения запросов с фронтенда.

## Особенности

- Интеграция с GigaChat для генерации вопросов и ответов
- Работа с PDF файлами для извлечения знаний
- Генерация вопросов с помощью LLM
- Оценивание ответов студентов
- Анализ эмоционального состояния
- Поддержка адаптивных экзаменов
