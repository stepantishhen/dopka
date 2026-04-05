from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Переменные приложения. extra='ignore' — игнорировать POSTGRES_PASSWORD и др. из .env/docker."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    gigachat_credentials: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    # Отдельная модель для оценки ответов (эталон vs студент). Пусто = та же, что openai_model
    openai_scoring_model: str = ""
    # Эмбеддинги для FAISS (размерность 384). По умолчанию лёгкая L3 (~60 МБ);
    # для лучшего русского: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (~420 МБ)
    embedding_model_name: str = "sentence-transformers/paraphrase-MiniLM-L3-v2"
    # Не вызывать проверку LLM при старте (офлайн-разработка)
    llm_skip_startup_check: bool = False
    database_url: str = "sqlite:///./exam_system.db"
    secret_key: str = "dev-secret-key-change-in-production"
    debug: bool = True
    # Предзаполнение: exam_test, демо-единицы БЗ, пользователи teacher/student@test.local (env: SEED_TEST_ENV)
    seed_test_env: bool = False
    cors_origins: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()

