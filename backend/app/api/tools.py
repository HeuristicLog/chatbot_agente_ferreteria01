import uuid
import time
import logging
from fastapi import APIRouter, Depends, Query, Body, HTTPException, status, Header
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from qdrant_client import AsyncQdrantClient

from app.db.session import get_db_session
from app.dependencies import get_redis, get_qdrant, verify_internal_auth, verify_write_actions_enabled
from app.services.auth_service import LogisticsAuthService
from app.services.ticket_service import TicketService
from app.services.notification_service import NotificationService
from app.services.logistic_operation_service import LogisticOperationService
from app.services.faq_service import FAQService
from app.services.handoff_service import HandoffService
from app.services.audit_service import AuditService
from app.services.session_service import SessionService
from app.security.masking import mask_driver_and_locations
from app.domain.models import FAQSearchRequest, HandoffRequest

logger = logging.getLogger("chatbot-api.api.tools")
router = APIRouter()

async def verify_session_logged_in(session_id: str, redis_client: redis.Redis) -> Optional[Dict[str, Any]]:
    """Helper to verify if a user session is logged in. Returns context dict if True, else None."""
    session_service = SessionService(None, redis_client)
    ctx = await session_service.get_session_context(session_id)
    if ctx.get("logged_in") is True:
        return ctx
    return None

def create_envelope(
    success: bool,
    data: Optional[Any] = None,
    message: str = "",
    error_code: Optional[str] = None,
    retryable: bool = False
) -> Dict[str, Any]:
    """Helper to envelope responses in a standard format."""
    error_detail = None
    if error_code:
        error_detail = {"code": error_code, "retryable": retryable}
    return {
        "success": success,
        "data": data,
        "message": message,
        "error": error_detail,
        "request_id": str(uuid.uuid4())
    }

# -----------------
# Internal Auth Status / Refresh
# -----------------
@router.post("/internal/auth/refresh", dependencies=[Depends(verify_internal_auth)])
async def force_token_refresh(
    redis_client: redis.Redis = Depends(get_redis)
):
    """Forces manual renewal of technical API token."""
    auth_service = LogisticsAuthService(redis_client)
    try:
        token = await auth_service.login()
        return create_envelope(True, {"status": "refreshed"}, "Token técnico renovado con éxito.")
    except Exception as e:
        return create_envelope(False, None, "No fue posible renovar el token.", "LOGIN_FAILED", False)

@router.get("/internal/auth/status", dependencies=[Depends(verify_internal_auth)])
async def get_token_status(
    redis_client: redis.Redis = Depends(get_redis)
):
    """Checks the status of cached technical token."""
    auth_service = LogisticsAuthService(redis_client)
    token = await redis_client.get(LogisticsAuthService.TOKEN_CACHE_KEY)
    if token:
        return create_envelope(True, {"cached": True, "token_prefix": token[:8]}, "Conexión técnica activa.")
    return create_envelope(True, {"cached": False}, "Sin conexión técnica activa.")

# -----------------
# Tools Endpoints (for Flowise)
# -----------------
async def log_tool_audit(
    db: AsyncSession,
    session_id: str,
    tool_name: str,
    payload: Dict[str, Any],
    start_time: float,
    status_code: Optional[int],
    success: bool,
    error_code: Optional[str] = None
):
    """Helper to register tool calls in audit DB log tables."""
    if not session_id:
        return
    try:
        audit = AuditService(db)
        duration = int((time.time() - start_time) * 1000)
        await audit.log_tool_call(
            session_id=session_id,
            tool_name=tool_name,
            request_payload=payload,
            response_status=status_code,
            success=success,
            duration_ms=duration,
            error_code=error_code
        )
    except Exception as e:
        logger.warning(f"Failed to log audit event: {str(e)}")

@router.get("/tools/me")
async def get_me(
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Exposes current technical account details."""
    start_time = time.time()
    session_ctx = await verify_session_logged_in(session_id, redis_client)
    if not session_ctx:
        return create_envelope(False, None, "Debe iniciar sesión para realizar esta acción. Por favor escribe 'iniciar sesión'.", "UNAUTHENTICATED", False)
        
    auth_service = LogisticsAuthService(redis_client, custom_token=session_ctx.get("driver_token"))
    ticket_service = TicketService(auth_service)
    
    try:
        res = await auth_service.execute_with_retry(ticket_service.api.get_me)
        await log_tool_audit(db, session_id, "consultar_usuario_actual", {}, start_time, 200, True)
        masked_data = mask_driver_and_locations(res.get("data", res))
        return create_envelope(True, masked_data, "Consulta realizada correctamente.")
    except Exception as e:
        await log_tool_audit(db, session_id, "consultar_usuario_actual", {}, start_time, 500, False, "GET_ME_ERROR")
        return create_envelope(False, None, "No fue posible consultar la información.", "LOGISTICS_API_UNAVAILABLE", True)

@router.get("/tools/tickets")
async def list_tickets(
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Lists driver tickets."""
    start_time = time.time()
    session_ctx = await verify_session_logged_in(session_id, redis_client)
    if not session_ctx:
        return create_envelope(False, None, "Debe iniciar sesión para realizar esta acción. Por favor escribe 'iniciar sesión'.", "UNAUTHENTICATED", False)
        
    auth_service = LogisticsAuthService(redis_client, custom_token=session_ctx.get("driver_token"))
    ticket_service = TicketService(auth_service)
    
    try:
        tickets = await ticket_service.get_tickets()
        await log_tool_audit(db, session_id, "consultar_tickets", {}, start_time, 200, True)
        masked_data = mask_driver_and_locations([t.model_dump() for t in tickets])
        return create_envelope(True, masked_data, "Consulta realizada correctamente.")
    except Exception as e:
        logger.error(f"Error listing tickets: {str(e)}")
        await log_tool_audit(db, session_id, "consultar_tickets", {}, start_time, 500, False, "LIST_TICKETS_ERROR")
        return create_envelope(False, None, "No fue posible consultar la información.", "LOGISTICS_API_UNAVAILABLE", True)

@router.get("/tools/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Retrieves specific ticket details."""
    start_time = time.time()
    session_ctx = await verify_session_logged_in(session_id, redis_client)
    if not session_ctx:
        return create_envelope(False, None, "Debe iniciar sesión para realizar esta acción. Por favor escribe 'iniciar sesión'.", "UNAUTHENTICATED", False)
        
    auth_service = LogisticsAuthService(redis_client, custom_token=session_ctx.get("driver_token"))
    ticket_service = TicketService(auth_service)
    
    try:
        ticket = await ticket_service.get_ticket_by_id(ticket_id)
        if not ticket:
            await log_tool_audit(db, session_id, "consultar_ticket_por_id", {"ticket_id": ticket_id}, start_time, 404, False, "TICKET_NOT_FOUND")
            return create_envelope(False, None, f"El ticket {ticket_id} no fue encontrado.", "TICKET_NOT_FOUND", False)
            
        await log_tool_audit(db, session_id, "consultar_ticket_por_id", {"ticket_id": ticket_id}, start_time, 200, True)
        masked_data = mask_driver_and_locations(ticket.model_dump())
        return create_envelope(True, masked_data, "Consulta realizada correctamente.")
    except Exception as e:
        logger.error(f"Error fetching ticket {ticket_id}: {str(e)}")
        await log_tool_audit(db, session_id, "consultar_ticket_por_id", {"ticket_id": ticket_id}, start_time, 500, False, "GET_TICKET_ERROR")
        return create_envelope(False, None, "No fue posible consultar la información.", "LOGISTICS_API_UNAVAILABLE", True)

@router.get("/tools/notifications")
async def list_notifications(
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Lists driver notifications."""
    start_time = time.time()
    session_ctx = await verify_session_logged_in(session_id, redis_client)
    if not session_ctx:
        return create_envelope(False, None, "Debe iniciar sesión para realizar esta acción. Por favor escribe 'iniciar sesión'.", "UNAUTHENTICATED", False)
        
    auth_service = LogisticsAuthService(redis_client, custom_token=session_ctx.get("driver_token"))
    notif_service = NotificationService(auth_service)
    
    try:
        notifications = await notif_service.get_notifications()
        await log_tool_audit(db, session_id, "consultar_notificaciones", {}, start_time, 200, True)
        masked_data = mask_driver_and_locations([n.model_dump() for n in notifications])
        return create_envelope(True, masked_data, "Consulta realizada correctamente.")
    except Exception as e:
        logger.error(f"Error listing notifications: {str(e)}")
        await log_tool_audit(db, session_id, "consultar_notificaciones", {}, start_time, 500, False, "LIST_NOTIF_ERROR")
        return create_envelope(False, None, "No fue posible consultar la información.", "LOGISTICS_API_UNAVAILABLE", True)

@router.get("/tools/novelty-reasons")
async def list_novelty_reasons(
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Lists novelty reasons."""
    start_time = time.time()
    session_ctx = await verify_session_logged_in(session_id, redis_client)
    if not session_ctx:
        return create_envelope(False, None, "Debe iniciar sesión para realizar esta acción. Por favor escribe 'iniciar sesión'.", "UNAUTHENTICATED", False)
        
    auth_service = LogisticsAuthService(redis_client, custom_token=session_ctx.get("driver_token"))
    notif_service = NotificationService(auth_service)
    
    try:
        reasons = await notif_service.get_novelty_reasons()
        await log_tool_audit(db, session_id, "consultar_motivos_novedad", {}, start_time, 200, True)
        return create_envelope(True, [r.model_dump() for r in reasons], "Consulta realizada correctamente.")
    except Exception as e:
        logger.error(f"Error listing novelty reasons: {str(e)}")
        await log_tool_audit(db, session_id, "consultar_motivos_novedad", {}, start_time, 500, False, "LIST_REASONS_ERROR")
        return create_envelope(False, None, "No fue posible consultar la información.", "LOGISTICS_API_UNAVAILABLE", True)

@router.get("/tools/logistic-operations")
async def list_operations(
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Lists logistic operations."""
    start_time = time.time()
    session_ctx = await verify_session_logged_in(session_id, redis_client)
    if not session_ctx:
        return create_envelope(False, None, "Debe iniciar sesión para realizar esta acción. Por favor escribe 'iniciar sesión'.", "UNAUTHENTICATED", False)
        
    auth_service = LogisticsAuthService(redis_client, custom_token=session_ctx.get("driver_token"))
    op_service = LogisticOperationService(auth_service)
    
    try:
        operations = await op_service.get_operations()
        await log_tool_audit(db, session_id, "consultar_operaciones_logisticas", {}, start_time, 200, True)
        masked_data = mask_driver_and_locations([o.model_dump() for o in operations])
        return create_envelope(True, masked_data, "Consulta realizada correctamente.")
    except Exception as e:
        logger.error(f"Error listing operations: {str(e)}")
        await log_tool_audit(db, session_id, "consultar_operaciones_logisticas", {}, start_time, 500, False, "LIST_OPS_ERROR")
        return create_envelope(False, None, "No fue posible consultar la información.", "LOGISTICS_API_UNAVAILABLE", True)

@router.get("/tools/logistic-operations/{operation_id}")
async def get_operation(
    operation_id: int,
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Gets details of specific logistic operation."""
    start_time = time.time()
    session_ctx = await verify_session_logged_in(session_id, redis_client)
    if not session_ctx:
        return create_envelope(False, None, "Debe iniciar sesión para realizar esta acción. Por favor escribe 'iniciar sesión'.", "UNAUTHENTICATED", False)
        
    auth_service = LogisticsAuthService(redis_client, custom_token=session_ctx.get("driver_token"))
    op_service = LogisticOperationService(auth_service)
    
    try:
        operation = await op_service.get_operation_by_id(operation_id)
        if not operation:
            await log_tool_audit(db, session_id, "consultar_operacion_logistica_por_id", {"operation_id": operation_id}, start_time, 404, False, "OP_NOT_FOUND")
            return create_envelope(False, None, f"La operación {operation_id} no fue encontrada.", "OPERATION_NOT_FOUND", False)
            
        await log_tool_audit(db, session_id, "consultar_operacion_logistica_por_id", {"operation_id": operation_id}, start_time, 200, True)
        masked_data = mask_driver_and_locations(operation.model_dump())
        return create_envelope(True, masked_data, "Consulta realizada correctamente.")
    except Exception as e:
        logger.error(f"Error getting operation {operation_id}: {str(e)}")
        await log_tool_audit(db, session_id, "consultar_operacion_logistica_por_id", {"operation_id": operation_id}, start_time, 500, False, "GET_OP_ERROR")
        return create_envelope(False, None, "No fue posible consultar la información.", "LOGISTICS_API_UNAVAILABLE", True)

@router.post("/tools/faq/search")
async def search_faq(
    req: FAQSearchRequest,
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    """Executes semantic or PostgreSQL keyword fallback FAQ lookup."""
    start_time = time.time()
    faq_service = FAQService(db, qdrant_client)
    
    try:
        results = await faq_service.search_faq(req.query, req.limit)
        await log_tool_audit(db, session_id, "buscar_pregunta_frecuente", {"query": req.query}, start_time, 200, True)
        return create_envelope(True, [r.model_dump() for r in results], "Consulta realizada correctamente.")
    except Exception as e:
        logger.error(f"FAQ search failed: {str(e)}")
        await log_tool_audit(db, session_id, "buscar_pregunta_frecuente", {"query": req.query}, start_time, 500, False, "FAQ_SEARCH_ERROR")
        return create_envelope(False, None, "No fue posible consultar las preguntas frecuentes.", "FAQ_SEARCH_ERROR", True)

@router.post("/tools/handoff")
async def request_human_handoff(
    req: HandoffRequest,
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    db: AsyncSession = Depends(get_db_session)
):
    """Triggers escalation to a human support agent."""
    start_time = time.time()
    handoff_service = HandoffService(db)
    
    try:
        handoff, assigned = await handoff_service.request_handoff(
            session_id=req.session_id,
            phone=req.phone,
            reason=req.reason,
            summary=req.summary,
            ticket_id=req.ticket_id,
            operation_id=req.operation_id,
            sucursal=req.sucursal,
            phone_number_id=req.phone_number_id
        )
        
        await log_tool_audit(db, session_id, "transferir_a_asesor", req.model_dump(), start_time, 200, True)
        return create_envelope(
            True, 
            {"handoff_id": str(handoff.id), "status": handoff.status, "assigned": assigned}, 
            "Transferencia registrada con éxito."
        )
    except Exception as e:
        logger.error(f"Handoff creation failed: {str(e)}")
        await log_tool_audit(db, session_id, "transferir_a_asesor", req.model_dump(), start_time, 500, False, "HANDOFF_ERROR")
        return create_envelope(False, None, "No fue posible registrar la transferencia.", "HANDOFF_ERROR", True)

@router.post("/tools/login")
async def login_session(
    session_id: str = Query(..., description="ID de sesión para auditoría"),
    email: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Logs a driver session in by verifying their credentials and caching their session status."""
    start_time = time.time()
    auth_service = LogisticsAuthService(redis_client)
    
    try:
        res = await auth_service.api.login(email, password, f"session-{session_id}")
        token = None
        if "token" in res:
            token = res["token"]
        elif "data" in res and isinstance(res["data"], dict) and "token" in res["data"]:
            token = res["data"]["token"]
        elif "token" in res.get("data", {}):
            token = res["data"]["token"]
            
        if not token:
            for key in ["token", "access_token", "jwt"]:
                if key in res:
                    token = res[key]
                    break
                    
        if not token:
            await log_tool_audit(db, session_id, "iniciar_sesion", {"email": email}, start_time, 400, False, "INVALID_RESPONSE")
            return create_envelope(False, None, "Credenciales inválidas o error en el servicio de logística.", "INVALID_CREDENTIALS", False)
            
        # Success! Save in session context
        session_service = SessionService(db, redis_client)
        await session_service.update_session_variables(session_id, {
            "logged_in": True,
            "driver_email": email,
            "driver_token": token
        })
        
        await log_tool_audit(db, session_id, "iniciar_sesion", {"email": email}, start_time, 200, True)
        return create_envelope(True, {"email": email, "logged_in": True}, "Inicio de sesión correcto. Ahora puedes consultar tus datos de ruta.")
        
    except Exception as e:
        logger.error(f"Error logging in session {session_id}: {str(e)}")
        await log_tool_audit(db, session_id, "iniciar_sesion", {"email": email}, start_time, 500, False, "LOGIN_ERROR")
        return create_envelope(False, None, "No fue posible iniciar sesión. Verifica tu correo y contraseña.", "INVALID_CREDENTIALS", False)
