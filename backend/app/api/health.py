import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from qdrant_client import AsyncQdrantClient

from app.db.session import get_db_session
from app.dependencies import get_redis, get_qdrant
from sqlalchemy import text

logger = logging.getLogger("chatbot-api.health")
router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Sanity check that the API is listening."""
    return {"status": "healthy", "service": "chatbot-api"}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    """Deep check verifying that all dependent backends are responding."""
    errors = {}
    
    # 1. PostgreSQL check
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness check failed for PostgreSQL: {str(e)}")
        errors["database"] = "Unreachable"

    # 2. Redis check
    try:
        await redis_client.ping()
    except Exception as e:
        logger.error(f"Readiness check failed for Redis: {str(e)}")
        errors["redis"] = "Unreachable"

    # 3. Qdrant check
    try:
        # Check basic collection list or health endpoint
        await qdrant_client.get_collections()
    except Exception as e:
        logger.error(f"Readiness check failed for Qdrant: {str(e)}")
        errors["qdrant"] = "Unreachable"

    if errors:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "checks": errors}
        )

    return {"status": "ready"}
