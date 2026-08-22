import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.db.session import get_db_session
from app.dependencies import get_redis, verify_internal_auth
from app.services.session_service import SessionService
from app.services.audit_service import AuditService
from app.services.flowise_service import FlowiseService
from app.security.sanitization import sanitize_user_input
from pydantic import BaseModel, Field

logger = logging.getLogger("chatbot-api.api.testing")
router = APIRouter()

class TestMessageRequest(BaseModel):
    phone: str = Field(..., example="593999999999")
    message: str = Field(..., example="Hola Castor, ¿cómo estás?")

@router.post("/test/messages", dependencies=[Depends(verify_internal_auth)])
async def test_conversation_endpoint(
    req: TestMessageRequest,
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Local simulation webhook to test the chatbot's conversational replies from a terminal/script."""
    session_service = SessionService(db, redis_client)
    audit_service = AuditService(db)
    flowise_service = FlowiseService()
    
    session_id = session_service.derive_session_id(req.phone)
    logger.info(f"[TEST RUN] Simulating inbound message for session {session_id}")
    
    # 1. Create session in PostgreSQL
    conv = await session_service.get_or_create_conversation(req.phone, provider="mock")
    
    # 2. Check Handoff bypass
    if conv.status == "handed_over":
        reply = "Actualmente estás transferido con un asesor humano. Por favor, espera a que tome tu mensaje y te responda por este canal."
        return {
            "session_id": session_id,
            "status": "handed_over",
            "reply": reply
        }
        
    # 3. Normal flow: Predict response
    sanitized_input = sanitize_user_input(req.message)
    
    # Log Inbound
    await audit_service.log_message(
        session_id=session_id,
        direction="inbound",
        role="user",
        content=sanitized_input,
        message_type="text"
    )
    
    # Call Flowise
    start_time = time.time()
    ai_response = await flowise_service.get_prediction(sanitized_input, session_id)
    duration = int((time.time() - start_time) * 1000)
    
    # Log Outbound
    await audit_service.log_message(
        session_id=session_id,
        direction="outbound",
        role="assistant",
        content=ai_response
    )
    
    return {
        "session_id": session_id,
        "phone": req.phone,
        "input_message": req.message,
        "sanitized_input": sanitized_input,
        "reply": ai_response,
        "duration_ms": duration
    }
