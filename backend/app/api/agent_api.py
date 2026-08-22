import logging
import uuid
import asyncio
import json
import httpx
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as redis
from typing import Dict, Any, List, Optional

from app.db.session import get_db_session
from app.db.tables import Conversation, Message, Seller, ConversationAssignment, ConversationNote, User
from app.dependencies import get_redis
from app.security.jwt_auth import decode_jwt_token
from app.config import settings

logger = logging.getLogger("chatbot-api.api.agent_api")
router = APIRouter()

# Read Gateway URL from env
GATEWAY_URL = "http://whatsapp-gateway:8090"
gateway_api_url = settings.LOGISTICS_API_BASE_URL # Or WHATSAPP_GATEWAY_URL

# Helper to verify JWT token and return seller ID
async def get_current_seller(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db_session)
) -> Seller:
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token de agente inválido o expirado.")
        
    email = payload.get("username") # username/email
    # Query database for seller profile
    stmt = select(Seller).where(Seller.email == payload.get("username"))
    res = await db.execute(stmt)
    seller = res.scalar_one_or_none()
    
    if not seller:
        # Fallback to query by user email
        stmt = select(Seller).where(Seller.email == payload.get("email", ""))
        res = await db.execute(stmt)
        seller = res.scalar_one_or_none()
        
    if not seller:
        raise HTTPException(status_code=403, detail="Vendedor no registrado en base de datos.")
    return seller

# Helper to publish SSE events to Redis
async def publish_sse_event(redis_client: redis.Redis, event_type: str, data: dict):
    try:
        payload = {"type": event_type, "data": data}
        await redis_client.publish("seller_updates", json.dumps(payload))
    except Exception as e:
        logger.warning(f"Failed to publish SSE event to Redis: {str(e)}")

# -----------------
# Seller Console Endpoints
# -----------------

@router.get("/api/v1/agent/chats")
async def list_agent_chats(
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session)
):
    """Lists chats assigned to the current seller, and chats in queue (waiting_agent)."""
    # 1. Fetch assigned chats
    stmt_assigned = select(Conversation).where(
        Conversation.current_seller_id == seller.id,
        Conversation.status.in_(["assigned", "human_active"])
    ).order_by(Conversation.last_activity_at.desc())
    res_assigned = await db.execute(stmt_assigned)
    assigned_convs = res_assigned.scalars().all()
    
    # 2. Fetch waiting chats in queue
    stmt_waiting = select(Conversation).where(
        Conversation.status == "waiting_agent"
    ).order_by(Conversation.started_at.asc())
    res_waiting = await db.execute(stmt_waiting)
    waiting_convs = res_waiting.scalars().all()
    
    return {
        "success": True,
        "assigned": [
            {
                "id": str(c.id),
                "session_id": c.session_id,
                "phone": c.phone_hash,
                "status": c.status,
                "last_activity": c.last_activity_at.isoformat() if c.last_activity_at else None
            }
            for c in assigned_convs
        ],
        "waiting": [
            {
                "id": str(c.id),
                "session_id": c.session_id,
                "phone": c.phone_hash,
                "status": c.status,
                "started_at": c.started_at.isoformat() if c.started_at else None
            }
            for c in waiting_convs
        ]
    }

@router.post("/api/v1/agent/chats/{conversation_id}/accept")
async def accept_chat(
    conversation_id: uuid.UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        
    # Update status to human_active
    conv.status = "human_active"
    conv.current_seller_id = seller.id
    
    # Update assignment status
    assign_stmt = select(ConversationAssignment).where(
        ConversationAssignment.conversation_id == conversation_id,
        ConversationAssignment.seller_id == seller.id
    ).order_by(ConversationAssignment.assigned_at.desc())
    assign_res = await db.execute(assign_stmt)
    assignment = assign_res.scalars().first()
    if assignment:
        assignment.status = "accepted"
        
    await db.commit()
    
    # Notify through SSE
    await publish_sse_event(redis_client, "chat_accepted", {
        "conversation_id": str(conversation_id),
        "seller_name": seller.name
    })
    
    return {"success": True, "message": "Conversación aceptada. El bot está pausado."}

@router.post("/api/v1/agent/chats/{conversation_id}/reject")
async def reject_chat(
    conversation_id: uuid.UUID,
    reason: str = Body(..., embed=True),
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        
    # Reset conversation back to waiting_agent
    conv.status = "waiting_agent"
    conv.current_seller_id = None
    
    # Decrease seller's active chats count
    if seller.active_chats > 0:
        seller.active_chats -= 1
        
    # Log rejection
    assign_stmt = select(ConversationAssignment).where(
        ConversationAssignment.conversation_id == conversation_id,
        ConversationAssignment.seller_id == seller.id
    ).order_by(ConversationAssignment.assigned_at.desc())
    assign_res = await db.execute(assign_stmt)
    assignment = assign_res.scalars().first()
    if assignment:
        assignment.status = "rejected"
        assignment.reject_reason = reason
        assignment.resolved_at = datetime.datetime.utcnow()
        
    await db.commit()
    
    # Publish rejection event
    await publish_sse_event(redis_client, "chat_rejected", {
        "conversation_id": str(conversation_id),
        "seller_name": seller.name,
        "reason": reason
    })
    
    return {"success": True, "message": "Conversación rechazada y colocada en cola nuevamente."}

@router.post("/api/v1/agent/chats/{conversation_id}/transfer")
async def transfer_chat(
    conversation_id: uuid.UUID,
    target_seller_id: uuid.UUID = Body(..., embed=True),
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    # 1. Fetch conversation
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        
    # 2. Fetch target seller
    target_stmt = select(Seller).where(Seller.id == target_seller_id)
    target_res = await db.execute(target_stmt)
    target_seller = target_res.scalar_one_or_none()
    if not target_seller or not target_seller.is_active or target_seller.status != "available":
        raise HTTPException(status_code=400, detail="El vendedor destino no está activo o disponible.")
        
    # Apply transfer
    conv.current_seller_id = target_seller.id
    conv.status = "assigned" # Back to assigned until target seller accepts
    
    # Decrease current load
    if seller.active_chats > 0:
        seller.active_chats -= 1
    # Increase target load
    target_seller.active_chats += 1
    
    # Log transfer assignment
    assignment = ConversationAssignment(
        conversation_id=conversation_id,
        seller_id=target_seller.id,
        status="pending",
        assigned_at=datetime.datetime.utcnow()
    )
    db.add(assignment)
    await db.commit()
    
    # Publish transfer event
    await publish_sse_event(redis_client, "chat_transferred", {
        "conversation_id": str(conversation_id),
        "from_seller": seller.name,
        "to_seller": target_seller.name
    })
    
    return {"success": True, "message": f"Conversación transferida a {target_seller.name}."}

@router.post("/api/v1/agent/chats/{conversation_id}/close")
async def close_chat(
    conversation_id: uuid.UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        
    conv.status = "closed"
    conv.closed_at = datetime.datetime.utcnow()
    
    # Decrement seller load
    if seller.active_chats > 0:
        seller.active_chats -= 1
        
    # Log resolution in assignments
    assign_stmt = select(ConversationAssignment).where(
        ConversationAssignment.conversation_id == conversation_id,
        ConversationAssignment.seller_id == seller.id
    ).order_by(ConversationAssignment.assigned_at.desc())
    assign_res = await db.execute(assign_stmt)
    assignment = assign_res.scalars().first()
    if assignment:
        assignment.status = "completed"
        assignment.resolved_at = datetime.datetime.utcnow()
        
    await db.commit()
    
    # Publish close event
    await publish_sse_event(redis_client, "chat_closed", {
        "conversation_id": str(conversation_id),
        "seller_name": seller.name
    })
    
    return {"success": True, "message": "Conversación cerrada con éxito. El bot se reactivará."}

# -----------------
# Chat Messages Endpoints
# -----------------
@router.get("/api/v1/agent/chats/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    res = await db.execute(stmt)
    messages = res.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "role": m.role,
                "content": m.content,
                "message_type": m.message_type,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    }

@router.post("/api/v1/agent/chats/{conversation_id}/messages")
async def send_agent_message(
    conversation_id: uuid.UUID,
    content: str = Body(..., embed=True),
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Sends a manual outbound WhatsApp message from the agent to the customer."""
    # 1. Fetch conversation details to get customer phone
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        
    # Save outbound message to DB
    new_msg = Message(
        conversation_id=conversation_id,
        direction="outbound",
        role="seller",
        content=content,
        message_type="text"
    )
    db.add(new_msg)
    await db.commit()
    await db.refresh(new_msg)
    
    # 2. Call WhatsApp gateway to deliver the message
    headers = {
        "X-Internal-API-Key": settings.INTERNAL_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Retrieve raw phone from Redis mapping
    raw_phone = await redis_client.get(f"phone_map:{conv.phone_hash}")
    if not raw_phone:
        raw_phone = conv.phone_hash
        logger.warning(f"Could not resolve raw phone for hash {conv.phone_hash}, using hash as fallback.")
        
    sent = False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://whatsapp-gateway:8090/send",
                json={"phone": raw_phone, "message": content},
                headers=headers,
                timeout=10.0
            )
            if resp.status_code == 200:
                sent = True
            else:
                logger.error(f"Gateway returned non-200 response: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"Failed to post manual message to WhatsApp gateway: {str(e)}")
        
    # Publish the message to Redis SSE channel
    await publish_sse_event(redis_client, "new_message", {
        "conversation_id": str(conversation_id),
        "direction": "outbound",
        "role": "seller",
        "content": content,
        "created_at": datetime.datetime.utcnow().isoformat()
    })
    
    return {"success": sent, "message": "Mensaje enviado a través de WhatsApp." if sent else "Mensaje guardado pero no enviado a WhatsApp."}

@router.post("/api/v1/agent/chats/{conversation_id}/notes")
async def add_chat_note(
    conversation_id: uuid.UUID,
    content: str = Body(..., embed=True),
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db_session)
):
    note = ConversationNote(
        conversation_id=conversation_id,
        seller_id=seller.id,
        content=content
    )
    db.add(note)
    await db.commit()
    return {"success": True, "message": "Nota interna registrada."}

# -----------------
# Real-Time SSE Endpoint
# -----------------
@router.get("/api/v1/agent/chats/realtime-sse")
async def sse_updates(
    token: str = Query(...),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Server-Sent Events connection for real-time seller assignment and chat updates."""
    # Verify token
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido para SSE.")
        
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("seller_updates")
        logger.info(f"SSE client connected for user: {payload.get('username')}")
        
        try:
            # Yield initial connection confirmation
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            
            while True:
                # Read message from Redis Pub/Sub
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    data = msg.get("data")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("SSE client connection closed (Cancelled).")
        finally:
            await pubsub.unsubscribe("seller_updates")
            await pubsub.close()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
