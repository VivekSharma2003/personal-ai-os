"""
Personal AI OS - Configuration Management
"""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/personal_ai_os",
        alias="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL"
    )
    
    # LLM Provider Selection
    llm_provider: Literal["openai", "gemini", "anthropic"] = Field(
        default="openai",
        alias="LLM_PROVIDER"
    )
    
    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")
    
    # Google Gemini
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-pro", alias="GEMINI_MODEL")
    
    # Anthropic
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", alias="ANTHROPIC_MODEL")
    
    # LLM Settings
    llm_temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    
    # Rule Engine
    confidence_threshold: float = Field(default=0.3, alias="CONFIDENCE_THRESHOLD")
    decay_rate: float = Field(default=0.05, alias="DECAY_RATE")
    archive_threshold: float = Field(default=0.2, alias="ARCHIVE_THRESHOLD")
    similarity_threshold: float = Field(default=0.85, alias="SIMILARITY_THRESHOLD")
    
    # Vector DB
    vector_db_path: str = Field(default="./data/vector_store", alias="VECTOR_DB_PATH")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    
    # Server
    debug: bool = Field(default=True, alias="DEBUG")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
