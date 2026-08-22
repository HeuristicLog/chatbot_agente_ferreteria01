import logging
from fastapi import Header, HTTPException, status, Depends
from typing import AsyncGenerator, Optional
import redis.asyncio as redis
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db_session

logger = logging.getLogger("chatbot-api.dependencies")

# Shared Redis pool
redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Dependency to retrieve an active Redis client connection."""
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.close()

async def get_qdrant() -> AsyncGenerator[AsyncQdrantClient, None]:
    """Dependency to retrieve an active Qdrant vector database client."""
    client = AsyncQdrantClient(url=settings.QDRANT_URL)
    try:
        yield client
    finally:
        await client.close()

def verify_internal_auth(x_internal_api_key: Optional[str] = Header(None, alias="X-Internal-API-Key")):
    """Dependency to guard internal endpoints using the configured shared API key."""
    if not x_internal_api_key or x_internal_api_key != settings.INTERNAL_API_KEY:
        logger.warning("Fallo de autenticacion interna. X-Internal-API-Key invalida o ausente.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Llave de API interna incorrecta o no provista."
        )

def verify_write_actions_enabled():
    """Dependency to block writing endpoints if ENABLE_WRITE_ACTIONS is set to false."""
    if not settings.ENABLE_WRITE_ACTIONS:
        logger.warning("Intento de ejecutar accion de escritura bloqueada (ENABLE_WRITE_ACTIONS=false).")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Las acciones de escritura están deshabilitadas en esta instancia del chatbot."
        )
