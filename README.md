# Система обучения для студентов и преподавателей

Фронтенд приложение на React с использованием Bootstrap для системы обучения с виртуальным экзаменатором.

## Возможности

### Для студентов:
- Экзамены - общение с виртуальным экзаменатором в режиме реального времени
- История - просмотр всех пройденных экзаменов
- Профиль - настройки и статистика обучения

### Для преподавателей:
- База знаний - управление учебными материалами (создание, редактирование, удаление)
- История - просмотр всех диалогов студентов
- Профиль - настройки и статистика системы

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

## Установка

### Backend

Требуется Python 3.11 или 3.12 (не рекомендуется Python 3.14 из-за несовместимости библиотеки `gigachat`)

1. Проверьте версию Python:
```bash
python --version
```

2. Перейдите в директорию backend:
```bash
cd backend
```

3. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

4. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env`:
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

### Frontend

1. Установите зависимости:
```bash
npm install
```

2. Создайте файл `.env` в корне проекта:
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

3. Запустите dev-сервер:
```bash
npm run dev
```

Приложение будет доступно по адресу `http://localhost:3000` или `http://localhost:5173`

## Структура проекта

```
.
├── backend/              # FastAPI backend
│   ├── main.py          # Точка входа
│   ├── config.py        # Конфигурация
│   ├── models/          # Модели данных
│   ├── schemas/         # API схемы
│   ├── services/        # Бизнес-логика
│   └── routers/         # API роутеры
├── src/                 # React frontend
│   ├── components/      # React компоненты
│   ├── pages/           # Страницы
│   ├── context/         # React Context
│   └── services/        # API сервисы
└── README.md
```

## API Endpoints

### База знаний
- `GET /api/knowledge-base/items` - Получить все элементы
- `POST /api/knowledge-base/items` - Создать элемент
- `PUT /api/knowledge-base/items/{id}` - Обновить элемент
- `DELETE /api/knowledge-base/items/{id}` - Удалить элемент
- `POST /api/knowledge-base/extract-from-text` - Извлечь из текста
- `POST /api/knowledge-base/extract-from-pdf` - Извлечь из PDF

### Чат
- `GET /api/chat` - Список чатов
- `POST /api/chat` - Создать чат
- `GET /api/chat/{id}` - Получить чат
- `POST /api/chat/{id}/message` - Отправить сообщение

### Экзамены
- `GET /api/exams` - Список экзаменов
- `POST /api/exams` - Создать экзамен
- `GET /api/exams/current` - Текущий экзамен
- `POST /api/exams/{id}/submit` - Отправить ответы

### Студенты
- `GET /api/students` - Список студентов
- `POST /api/students` - Создать профиль
- `GET /api/students/{id}` - Профиль студента
- `POST /api/students/{id}/emotional-state` - Оценить состояние
- `POST /api/students/{id}/diagnostic` - Диагностика

## Особенности

- Система ролей - разделение интерфейса для студентов и преподавателей
- Виртуальный экзаменатор - интерактивное общение для проверки знаний
- База знаний - управление учебными материалами (только для преподавателей)
- Интеграция с GigaChat - генерация вопросов и ответов с помощью LLM
- Извлечение знаний из PDF - автоматическое создание дидактических единиц
- Анализ эмоционального состояния - оценка психологического настроя студентов
- Адаптивные экзамены - персонализированные тесты
- CORS поддержка - готово для работы с фронтендом

## Использование

1. Запустите backend сервер (порт 8000)
2. Запустите frontend приложение (порт 3000/5173)
3. При первом запуске выберите роль (Студент или Преподаватель)
4. Студенты могут начинать новые экзамены и общаться с виртуальным экзаменатором
5. Преподаватели могут управлять базой знаний и просматривать историю диалогов студентов

## Разработка

### Локальная разработка

Для разработки рекомендуется запускать оба сервера одновременно:

```bash
# Терминал 1 - Backend
cd backend
python -m uvicorn backend.main:app --reload

# Терминал 2 - Frontend
npm run dev
```

### Docker

#### Production сборка

1. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

2. Настройте переменные окружения в `.env`

3. Запустите с Docker Compose:
```bash
docker-compose up -d
```

Приложение будет доступно:
- Frontend: http://localhost
- Backend API: http://localhost:8000
- API документация: http://localhost:8000/docs

#### Development режим

Для разработки с hot-reload:

```bash
docker-compose -f docker-compose.dev.yml up
```

- Frontend: http://localhost:3000 (с hot-reload)
- Backend API: http://localhost:8000 (с auto-reload)

#### Остановка

```bash
docker-compose down
```

Для удаления volumes (данные БД):
```bash
docker-compose down -v
```

## Лицензия

MIT
