import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gigachat_credentials: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./exam_system.db"
    secret_key: str = "dev-secret-key-change-in-production"
    debug: bool = True
    cors_origins: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173"
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

