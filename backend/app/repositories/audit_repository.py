import uuid
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from datetime import datetime

from app.db.tables import ToolCall, Handoff

logger = logging.getLogger("chatbot-api.repositories.audit")

class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_tool_call(
        self,
        conversation_id: uuid.UUID,
        tool_name: str,
        request_payload: Dict[str, Any],
        response_status: Optional[int],
        success: bool,
        duration_ms: int,
        error_code: Optional[str] = None
    ) -> ToolCall:
        """Saves a tool execution event record to the audit tables."""
        tool_call = ToolCall(
            conversation_id=conversation_id,
            tool_name=tool_name,
            request_payload=request_payload,
            response_status=response_status,
            success=success,
            duration_ms=duration_ms,
            error_code=error_code
        )
        self.db.add(tool_call)
        await self.db.commit()
        await self.db.refresh(tool_call)
        return tool_call

    async def create_handoff(
        self,
        conversation_id: uuid.UUID,
        phone_hash: str,
        reason: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Handoff:
        """Registers a pending human support agent handoff request."""
        handoff = Handoff(
            conversation_id=conversation_id,
            phone_hash=phone_hash,
            reason=reason,
            summary=summary,
            status="pending",
            metadata_json=metadata or {}
        )
        self.db.add(handoff)
        await self.db.commit()
        await self.db.refresh(handoff)
        return handoff

    async def get_active_handoff(self, conversation_id: uuid.UUID) -> Optional[Handoff]:
        """Retrieves active or pending handoff requests for a conversation session."""
        stmt = (
            select(Handoff)
            .where(
                (Handoff.conversation_id == conversation_id) & 
                (Handoff.status.in_(["pending", "active"]))
            )
            .order_by(Handoff.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def resolve_handoff(self, handoff_id: uuid.UUID, resolved_by: str) -> None:
        """Marks a handoff request as resolved by an agent."""
        stmt = (
            update(Handoff)
            .where(Handoff.id == handoff_id)
            .values(status="resolved", resolved_at=datetime.utcnow(), assigned_to=resolved_by)
        )
        await self.db.execute(stmt)
        await self.db.commit()
