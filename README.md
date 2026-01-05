# Система обучения с виртуальным экзаменатором

Мульти-агентная система для обучения студентов с использованием LLM и адаптивных экзаменов.

## Возможности

### Для студентов:
- Экзамены в диалоговом режиме с виртуальным экзаменатором
- Адаптивные вопросы на основе производительности
- Уточняющие вопросы и обратная связь
- История пройденных экзаменов
- Профиль и статистика обучения

### Для преподавателей:
- Создание экзаменов из материалов (текст/PDF)
- Управление базой знаний
- Просмотр истории диалогов студентов
- Аналитика и метрики системы
- Профиль и настройки

## Технологии

### Frontend:
- React 18
- React Router DOM 6
- Bootstrap 5
- React Bootstrap 2
- Vite

### Backend:
- FastAPI
- GigaChat API
- Sentence Transformers
- FAISS
- NetworkX
- Python 3.12

## Быстрый старт

### Запуск через Docker Compose

```bash
sudo docker compose -f docker-compose.dev.yml up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Локальная установка

#### Backend

1. Python 3.11 или 3.12 (не рекомендуется 3.14)
2. Создайте виртуальное окружение:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Создайте `.env`:
```env
GIGACHAT_CREDENTIALS=your_credentials_here
DATABASE_URL=sqlite:///./exam_system.db
SECRET_KEY=your-secret-key-here
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

4. Запустите:
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
npm install
npm run dev
```

## Архитектура

Мульти-агентная система с оркестратором:

- **Core Orchestrator** - управление workflow между агентами
- **Knowledge Agent** - работа с базой знаний, семантический поиск
- **Dialogue Agent** - ведение диалога, уточняющие вопросы
- **Critic Agent** - оценка ответов, анализ рассуждений
- **Planning Agent** - адаптивный выбор вопросов
- **Analytics Agent** - сбор метрик и аналитика

## API Endpoints

### Оркестратор (`/api/orchestrator`)
- `POST /sessions` - Создание сессии
- `GET /sessions/{id}` - Получение сессии
- `POST /sessions/{id}/answer` - Отправка ответа
- `POST /sessions/{id}/next-question` - Следующий вопрос
- `POST /sessions/{id}/insights` - Инсайты
- `GET /sessions/{id}/dialogue` - История диалога

### Экзамены (`/api/exams`)
- `GET /` - Список экзаменов
- `GET /{exam_id}` - Получить экзамен
- `POST /create-from-materials` - Создать из текста
- `POST /create-from-pdf` - Создать из PDF

### База знаний (`/api/knowledge-base`)
- `GET /items` - Все элементы
- `POST /items` - Создать элемент
- `POST /extract-from-text` - Извлечь из текста
- `POST /extract-from-pdf` - Извлечь из PDF
- `POST /units/{unit_id}/generate-questions` - Генерация вопросов

### Метрики
- `GET /api/metrics` - Метрики системы

## Создание экзаменов

### Через интерфейс

1. Перейдите в "База знаний" (преподаватель)
2. Нажмите "Создать экзамен из материалов"
3. Выберите способ: текст или PDF
4. Заполните параметры и создайте экзамен

### Через API

```bash
POST /api/exams/create-from-materials
{
  "name": "Экзамен по Python",
  "text": "Текст материала...",
  "num_questions": 10,
  "adaptive": true
}
```

## Workflow диалогового режима

1. Студент выбирает экзамен → `/exam/{examId}`
2. Система загружает экзамен и создает сессию
3. Студент отвечает на вопросы
4. Critic Agent оценивает ответ
5. При неверном ответе → Dialogue Agent генерирует уточняющий вопрос
6. Студент может ответить снова
7. После правильного ответа → переход к следующему вопросу

## Структура проекта

```
.
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   │   ├── orchestrator.py
│   │   ├── agents/
│   │   ├── knowledge_service.py
│   │   └── exam_service.py
│   ├── routers/
│   └── middleware/
├── src/
│   ├── components/
│   ├── pages/
│   ├── context/
│   └── services/
└── README.md
```

## Особенности

- Мульти-агентная архитектура
- Адаптивные экзамены
- Диалоговый режим с уточняющими вопросами
- Семантический поиск через FAISS
- Генерация вопросов через LLM
- Аналитика и метрики
- Извлечение знаний из PDF

## Лицензия

MIT
