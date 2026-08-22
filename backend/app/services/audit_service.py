import json
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repository import AuditRepository
from app.repositories.conversation_repository import ConversationRepository
from app.db.tables import ToolCall, Message

logger = logging.getLogger("chatbot-api.audit")

class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_repo = AuditRepository(db)
        self.conv_repo = ConversationRepository(db)

    def _write_structured_log(
        self,
        level: str,
        event: str,
        session_id: str,
        request_id: Optional[str] = None,
        duration_ms: int = 0,
        success: bool = True,
        tool: Optional[str] = None,
        error_code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Prints a structured JSON log message to stdout for aggregation."""
        log_payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "event": event,
            "session_id": session_id,
            "request_id": request_id or "",
            "duration_ms": duration_ms,
            "success": success,
            "tool": tool or "",
            "error_code": error_code or "",
        }
        if extra:
            log_payload.update(extra)
            
        print(json.dumps(log_payload))

    async def log_message(
        self,
        session_id: str,
        direction: str,
        role: str,
        content: str,
        message_type: str = "text",
        external_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Appends a message log to the DB and writes a structured system log."""
        conv = await self.conv_repo.get_by_session_id(session_id)
        if not conv:
            raise ValueError(f"No conversation found for session ID {session_id}")
            
        msg = await self.conv_repo.add_message(
            conversation_id=conv.id,
            direction=direction,
            role=role,
            content=content,
            message_type=message_type,
            external_message_id=external_id,
            metadata=metadata
        )
        
        # Log to stdout
        self._write_structured_log(
            level="INFO",
            event="message_recorded",
            session_id=session_id,
            extra={"direction": direction, "role": role, "message_id": str(msg.id)}
        )
        return msg

    async def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        request_payload: Dict[str, Any],
        response_status: Optional[int],
        success: bool,
        duration_ms: int,
        error_code: Optional[str] = None
    ) -> ToolCall:
        """Saves a tool invocation event to the DB and writes a structured log."""
        conv = await self.conv_repo.get_by_session_id(session_id)
        if not conv:
            raise ValueError(f"No conversation found for session ID {session_id}")
            
        # Sanitise request payload before saving
        from app.security.masking import mask_sensitive_keys
        sanitized_payload = mask_sensitive_keys(request_payload)
        
        tool_call = await self.audit_repo.log_tool_call(
            conversation_id=conv.id,
            tool_name=tool_name,
            request_payload=sanitized_payload,
            response_status=response_status,
            success=success,
            duration_ms=duration_ms,
            error_code=error_code
        )
        
        self._write_structured_log(
            level="INFO" if success else "ERROR",
            event="tool_call",
            session_id=session_id,
            tool=tool_name,
            success=success,
            duration_ms=duration_ms,
            error_code=error_code,
            extra={"response_status": response_status}
        )
        return tool_call
