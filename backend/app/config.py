import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    APP_ENV: str = Field("development")
    APP_TIMEZONE: str = Field("America/Guayaquil")
    
    # DB & Caches
    DATABASE_URL: str = Field("postgresql+asyncpg://chatbot:change_me@postgres:5432/ferreteria_chatbot")
    REDIS_URL: str = Field("redis://redis:6379/0")
    QDRANT_URL: str = Field("http://qdrant:6333")
    QDRANT_COLLECTION: str = Field("ferreteria_faq")
    
    # Logistics API
    LOGISTICS_API_BASE_URL: str = Field("http://host.docker.internal:8000")
    LOGISTICS_API_EMAIL: str = Field("")
    LOGISTICS_API_PASSWORD: str = Field("")
    LOGISTICS_API_DEVICE_NAME: str = Field("flowise-chatbot")
    LOGISTICS_API_TIMEOUT_SECONDS: int = Field(15)
    
    # Flowise
    FLOWISE_BASE_URL: str = Field("http://flowise:3000")
    FLOWISE_CHATFLOW_ID: str = Field("")
    FLOWISE_API_KEY: str = Field("")
    
    # Internal Auth / Gateways
    INTERNAL_API_KEY: str = Field("change_me")
    ENABLE_WRITE_ACTIONS: bool = Field(False)
    SESSION_TTL_MINUTES: int = Field(60)
    RATE_LIMIT_MESSAGES_PER_MINUTE: int = Field(20)
    
    # LLM Settings
    LLM_PROVIDER: str = Field("openai")
    LLM_MODEL: str = Field("gpt-4o-mini")
    LLM_API_KEY: str = Field("")
    
    # Embeddings
    EMBEDDING_PROVIDER: str = Field("openai")
    EMBEDDING_MODEL: str = Field("text-embedding-3-small")
    EMBEDDING_API_KEY: str = Field("")
    
    # Logging
    LOG_LEVEL: str = Field("INFO")

    # Chatwoot Integration
    CHATWOOT_BASE_URL: str = Field("http://chatwoot-web:3000")
    CHATWOOT_API_TOKEN: str = Field("")
    CHATWOOT_ACCOUNT_ID: int = Field(1)
    CHATWOOT_INBOX_ID: int = Field(1)
    WHATSAPP_INBOX_MAPPING: str = Field("{}")

    @property
    def whatsapp_inbox_mapping(self) -> dict:
        import json
        try:
            return json.loads(self.WHATSAPP_INBOX_MAPPING)
        except Exception:
            return {}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
