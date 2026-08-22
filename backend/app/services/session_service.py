import re
import hashlib
import json
import logging
import redis.asyncio as redis
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.conversation_repository import ConversationRepository
from app.db.tables import Conversation

logger = logging.getLogger("chatbot-api.services.session")

class SessionService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.repo = ConversationRepository(db)
        self.redis = redis_client
        self.ttl = settings.SESSION_TTL_MINUTES * 60

    @staticmethod
    def derive_session_id(phone: str, phone_number_id: Optional[str] = None) -> str:
        """Derives a session ID by hashing the phone number to preserve privacy."""
        clean_phone = re.sub(r"\D", "", phone) # Strip non-digits
        if phone_number_id:
            clean_phone = f"{phone_number_id}_{clean_phone}"
        hasher = hashlib.sha256()
        hasher.update(clean_phone.encode("utf-8"))
        return f"sess_{hasher.hexdigest()[:32]}"

    @staticmethod
    def derive_phone_hash(phone: str) -> str:
        """Derives a hashed phone string for database lookup."""
        clean_phone = re.sub(r"\D", "", phone)
        hasher = hashlib.sha256()
        hasher.update(clean_phone.encode("utf-8"))
        return hasher.hexdigest()

    async def get_or_create_conversation(self, phone: str, provider: str = "mock", phone_number_id: Optional[str] = None) -> Conversation:
        """Looks up or inserts the conversation metadata in the database."""
        session_id = self.derive_session_id(phone, phone_number_id)
        phone_hash = self.derive_phone_hash(phone)
        
        conv = await self.repo.get_by_session_id(session_id)
        if not conv:
            logger.info(f"Creating new conversation for session {session_id}")
            conv = await self.repo.create(session_id, phone_hash, provider)
        else:
            logger.debug(f"Retrieved existing conversation for session {session_id}")
        return conv

    # -----------------
    # Redis Session Memory Cache
    # -----------------
    def _redis_key(self, session_id: str) -> str:
        return f"session:context:{session_id}"

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieves short-term conversation context from Redis."""
        key = self._redis_key(session_id)
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except Exception:
                logger.error(f"Error parsing session context JSON: {data}")
        return {}

    async def save_session_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Caches session context variables in Redis with expiration TTL."""
        key = self._redis_key(session_id)
        await self.redis.set(key, json.dumps(context), ex=self.ttl)

    async def update_session_variables(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates specific parameters in the Redis context cache."""
        context = await self.get_session_context(session_id)
        context.update(updates)
        await self.save_session_context(session_id, context)
        return context

    async def clear_session_context(self, session_id: str) -> None:
        """Cleans up cached variables for a session."""
        key = self._redis_key(session_id)
        await self.redis.delete(key)
