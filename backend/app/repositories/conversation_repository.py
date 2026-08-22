import uuid
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.tables import Conversation, Message

logger = logging.getLogger("chatbot-api.repositories.conversation")

class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_session_id(self, session_id: str) -> Optional[Conversation]:
        """Retrieves a conversation record by its unique session ID."""
        stmt = select(Conversation).where(Conversation.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, session_id: str, phone_hash: str, provider: str = "mock", metadata: Optional[Dict[str, Any]] = None) -> Conversation:
        """Creates and persists a new conversation record."""
        conv = Conversation(
            session_id=session_id,
            phone_hash=phone_hash,
            provider=provider,
            metadata_json=metadata or {},
            status="active"
        )
        self.db.add(conv)
        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def update_activity(self, conversation_id: uuid.UUID) -> None:
        """Updates the last activity timestamp of a conversation."""
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_activity_at=datetime.utcnow())
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def close_session(self, session_id: str) -> None:
        """Marks a conversation session as closed."""
        stmt = (
            update(Conversation)
            .where(Conversation.session_id == session_id)
            .values(status="closed", closed_at=datetime.utcnow())
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        direction: str,
        role: str,
        content: str,
        message_type: str = "text",
        external_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Appends a message to the conversation message table."""
        msg = Message(
            conversation_id=conversation_id,
            direction=direction,
            role=role,
            content=content,
            message_type=message_type,
            external_message_id=external_message_id,
            metadata_json=metadata or {}
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        
        # Proactively update conversation activity
        await self.update_activity(conversation_id)
        return msg

    async def get_recent_messages(self, conversation_id: uuid.UUID, limit: int = 10) -> List[Message]:
        """Retrieves recent messages in chronological order for chatbot context window."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        # Reverse to return chronological order
        msgs = list(result.scalars().all())
        msgs.reverse()
        return msgs
