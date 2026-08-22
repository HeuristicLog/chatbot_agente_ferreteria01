import logging
import time
import httpx
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import AsyncQdrantClient
import redis.asyncio as redis
from typing import Dict, Any, List, Optional

from app.db.session import get_db_session
from app.db.tables import Conversation, Message, Handoff
from app.dependencies import get_redis, get_qdrant
from app.services.auth_service import LogisticsAuthService
from app.services.faq_service import FAQService
from app.services.assignment_service import AssignmentService
from app.clients.logistics_api import LogisticsApiClient, LogisticsApiError

logger = logging.getLogger("chatbot-api.api.chat")
router = APIRouter()

# Technical state translator to Spanish
STATUS_TRANSLATOR = {
    "created": "Pedido creado",
    "sent_to_warehouse": "Enviado al almacén",
    "assigned_to_warehouse": "Asignado en almacén",
    "picking": "Preparando el pedido (picking)",
    "loading": "Cargando el pedido",
    "loaded": "Cargado",
    "dispatched": "Pedido despachado",
    "in_route": "Pedido en ruta",
    "delivered": "Pedido entregado",
    "delivery_failed": "No se pudo completar la entrega",
    "returning": "Pedido en proceso de retorno",
    "arrived_back": "Retornado al almacén",
    "cancelled": "Pedido cancelado"
}

def translate_status(tech_status: str) -> str:
    return STATUS_TRANSLATOR.get(tech_status, tech_status)

def create_envelope(success: bool, data: Optional[Any] = None, message: str = "", error_code: Optional[str] = None) -> Dict[str, Any]:
    error_detail = None
    if error_code:
        error_detail = {"code": error_code, "details": None}
    return {
        "success": success,
        "data": data,
        "message": message,
        "error": error_detail,
        "correlation_id": str(uuid.uuid4())
    }

# -----------------
# Chat Façade Endpoints
# -----------------

@router.post("/api/chat/faq/search")
async def search_faq(
    query: str = Body(..., embed=True),
    session_id: str = Query(..., description="ID de sesión conversacional"),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    """Executes semantic lookup against Qdrant, with database fallback."""
    faq_service = FAQService(db, qdrant_client)
    try:
        results = await faq_service.search_faq(query, limit=3)
        return create_envelope(True, [r.model_dump() for r in results], "Búsqueda de FAQ completada.")
    except Exception as e:
        logger.error(f"Error searching FAQ: {str(e)}")
        return create_envelope(False, None, "Error al consultar las preguntas frecuentes.", "FAQ_SEARCH_ERROR")

@router.get("/api/chat/tickets/{ticket_id}/status")
async def get_ticket_status(
    ticket_id: int,
    phone: str = Query(..., description="Teléfono del cliente para validación"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Securely fetches ticket status and translates it, checking customer ownership."""
    auth_service = LogisticsAuthService(redis_client)
    client = LogisticsApiClient()
    
    try:
        # Call logistics API using technical service account token
        res = await auth_service.execute_with_retry(client.get_ticket_by_id, ticket_id)
        ticket = res.get("data", {})
        
        # Verify ownership to prevent ticket enumeration
        cust_phone = ticket.get("customer_phone")
        if not cust_phone or (phone not in cust_phone and cust_phone not in phone):
            # Unauthorized lookup
            logger.warning(f"Unauthorized ticket lookup attempt: phone {phone} requested ticket {ticket_id} (belongs to {cust_phone})")
            return create_envelope(False, None, "El ticket no pertenece al número de contacto proporcionado.", "TICKET_OWNERSHIP_MISMATCH")
            
        # Strip sensitive driver and GPS details
        safe_ticket = {
            "id": ticket.get("id"),
            "status": translate_status(ticket.get("status")),
            "description": ticket.get("description"),
            "occurred_at": ticket.get("occurred_at"),
            "items": ticket.get("items", []),
            "order_number": ticket.get("order_number")
        }
        return create_envelope(True, safe_ticket, "Detalles del ticket consultados con éxito.")
    except LogisticsApiError as e:
        if e.status_code == 404:
            return create_envelope(False, None, "El ticket solicitado no existe.", "TICKET_NOT_FOUND")
        return create_envelope(False, None, "No fue posible consultar el ticket.", "LOGISTICS_API_UNAVAILABLE")
    except Exception as e:
        logger.error(f"Error fetching ticket status: {str(e)}")
        return create_envelope(False, None, "Error al consultar el estado del ticket.", "INTERNAL_ERROR")

@router.get("/api/chat/orders/{order_number}/status")
async def get_order_status(
    order_number: str,
    phone: str = Query(..., description="Teléfono del cliente para validación"),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Looks up order by order_number and validates customer ownership."""
    auth_service = LogisticsAuthService(redis_client)
    client = LogisticsApiClient()
    
    try:
        res = await auth_service.execute_with_retry(client.get_tickets)
        tickets = res.get("data", [])
        
        # Find ticket with matching order number
        matching_ticket = None
        for t in tickets:
            if t.get("order_number") == order_number:
                matching_ticket = t
                break
                
        if not matching_ticket:
            return create_envelope(False, None, "El pedido no fue encontrado.", "ORDER_NOT_FOUND")
            
        # Verify ownership
        cust_phone = matching_ticket.get("customer_phone")
        if not cust_phone or (phone not in cust_phone and cust_phone not in phone):
            logger.warning(f"Unauthorized order lookup attempt: phone {phone} requested order {order_number} (belongs to {cust_phone})")
            return create_envelope(False, None, "El pedido no pertenece al número de contacto proporcionado.", "ORDER_OWNERSHIP_MISMATCH")
            
        safe_order = {
            "id": matching_ticket.get("id"),
            "status": translate_status(matching_ticket.get("status")),
            "description": matching_ticket.get("description"),
            "items": matching_ticket.get("items", []),
            "order_number": matching_ticket.get("order_number"),
            "occurred_at": matching_ticket.get("occurred_at")
        }
        return create_envelope(True, safe_order, "Detalles del pedido consultados con éxito.")
    except Exception as e:
        logger.error(f"Error fetching order status: {str(e)}")
        return create_envelope(False, None, "Error al consultar el estado del pedido.", "INTERNAL_ERROR")

@router.get("/api/chat/logistic-operations/{id}/status")
async def get_operation_status(
    id: int,
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Fetches logistic operation details and translates status, hiding GPS data."""
    auth_service = LogisticsAuthService(redis_client)
    client = LogisticsApiClient()
    
    try:
        res = await auth_service.execute_with_retry(client.get_logistic_operation_by_id, id)
        op = res.get("data", {})
        
        # Format stops nicely
        stops = op.get("stops", [])
        formatted_stops = [
            {
                "stop_name": s.get("stop_name"),
                "status": "Completada" if s.get("status") == "finished" else "Pendiente"
            }
            for s in stops
        ]
        
        # Translate main operation status
        op_status = translate_status(op.get("status", ""))
        
        safe_op = {
            "id": op.get("id"),
            "status": op_status,
            "route": op.get("route"),
            "stops": formatted_stops
        }
        return create_envelope(True, safe_op, "Detalles de la operación logística consultados.")
    except Exception as e:
        logger.error(f"Error fetching operations: {str(e)}")
        return create_envelope(False, None, "No fue posible consultar la operación logística.", "OPERATION_NOT_FOUND")

@router.post("/api/chat/handoff")
async def request_handoff(
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Triggers seller allocation and transitions conversation status to waiting_agent."""
    session_id = payload.get("session_id")
    phone = payload.get("phone")
    reason = payload.get("reason", "Solicitud de asistencia humana")
    specialty = payload.get("specialty")
    
    if not session_id or not phone:
        raise HTTPException(status_code=400, detail="session_id y phone son obligatorios.")
        
    try:
        # Find conversation
        from sqlalchemy import select
        stmt = select(Conversation).where(Conversation.session_id == session_id)
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no encontrada.")
            
        conv.status = "waiting_agent"
        await db.commit()
        
        # Log Handoff request
        handoff = Handoff(
            conversation_id=conv.id,
            phone_hash=phone,
            reason=reason,
            status="pending"
        )
        db.add(handoff)
        await db.commit()
        
        # Run assignment service
        assign_service = AssignmentService(db)
        assigned_seller = await assign_service.assign_conversation_to_seller(conv.id, specialty_needed=specialty)
        
        if assigned_seller:
            return create_envelope(True, {
                "assigned": True,
                "seller_name": assigned_seller.name,
                "seller_phone": assigned_seller.whatsapp_phone,
                "status": "assigned"
            }, f"Conversación asignada al asesor {assigned_seller.name}.")
        else:
            return create_envelope(True, {
                "assigned": False,
                "status": "waiting_agent",
                "message": "Todos los asesores están ocupados. Has sido colocado en cola de espera."
            }, "Derivación en espera.")
            
    except Exception as e:
        logger.error(f"Handoff error: {str(e)}")
        return create_envelope(False, None, "No fue posible registrar la transferencia.", "HANDOFF_ERROR")
