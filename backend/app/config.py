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

    # Webhooks
    webhook_timeout: int = Field(default=10, alias="WEBHOOK_TIMEOUT")
    webhook_max_retries: int = Field(default=3, alias="WEBHOOK_MAX_RETRIES")

    # Conflict Detection
    conflict_scan_interval: int = Field(default=6, alias="CONFLICT_SCAN_INTERVAL_HOURS")

    # Rate Limiting
    rate_limit_default: int = Field(default=60, alias="RATE_LIMIT_DEFAULT")
    rate_limit_llm: int = Field(default=10, alias="RATE_LIMIT_LLM")
    rate_limit_burst: int = Field(default=5, alias="RATE_LIMIT_BURST")

    # Data Retention (days, 0 = keep forever)
    retention_interactions_days: int = Field(default=90, alias="RETENTION_INTERACTIONS_DAYS")
    retention_audit_days: int = Field(default=365, alias="RETENTION_AUDIT_DAYS")
    retention_conversations_days: int = Field(default=180, alias="RETENTION_CONVERSATIONS_DAYS")

    # LLM Budget Guardrails (USD, 0 = unlimited)
    llm_budget_daily_usd: float = Field(default=5.0, alias="LLM_BUDGET_DAILY_USD")
    llm_budget_monthly_usd: float = Field(default=100.0, alias="LLM_BUDGET_MONTHLY_USD")

    # Rule Lifecycle
    lifecycle_stale_days: int = Field(default=30, alias="LIFECYCLE_STALE_DAYS")
    lifecycle_auto_archive: bool = Field(default=True, alias="LIFECYCLE_AUTO_ARCHIVE")

    # A/B Experiments
    experiment_min_sample: int = Field(default=50, alias="EXPERIMENT_MIN_SAMPLE")

    # Clustering
    cluster_similarity_threshold: float = Field(default=0.75, alias="CLUSTER_SIMILARITY_THRESHOLD")

    # Replay
    replay_max_concurrent: int = Field(default=5, alias="REPLAY_MAX_CONCURRENT")

    # Notifications
    notification_digest_hour: int = Field(default=8, alias="NOTIFICATION_DIGEST_HOUR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
