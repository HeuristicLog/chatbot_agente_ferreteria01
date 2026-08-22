import logging
import uuid
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from typing import List, Dict, Any, Optional

from app.db.session import get_db_session
from app.db.tables import FAQDocument, FAQCategory, FAQVersion, Seller, User, AuditLog
from app.dependencies import get_qdrant, get_redis
from app.services.faq_service import FAQService
from app.security.jwt_auth import decode_jwt_token, create_jwt_token, verify_password
from app.config import settings

logger = logging.getLogger("chatbot-api.api.admin_api")
router = APIRouter()

# Security Dependency
async def get_current_admin(
    token: Optional[str] = Query(None), # can pass in query or auth header
    authorization: Optional[str] = Depends(lambda: None) # placeholder
) -> Dict[str, Any]:
    # Check Authorization header if not query parameter
    # For simplicity, we decode the token
    if not token:
        # Fallback to check header (mock header checking or dummy authorization)
        token = "dummy" # fallback
        
    payload = decode_jwt_token(token)
    if not payload or payload.get("role") not in ["super_admin", "admin", "content_manager", "supervisor"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado. Token inválido o permisos insuficientes."
        )
    return payload

async def log_audit(db: AsyncSession, user_id: str, action: str, details: str):
    try:
        log = AuditLog(
            user_id=uuid.UUID(user_id) if user_id else None,
            action=action,
            details=details
        )
        db.add(log)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit action: {str(e)}")

# -----------------
# Admin Auth Endpoints
# -----------------
@router.post("/api/v1/admin/auth/login")
async def admin_login(
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    email = payload.get("email")
    password = payload.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y contraseña requeridos.")
        
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")
        
    if user.role not in ["super_admin", "admin", "content_manager", "supervisor"]:
        raise HTTPException(status_code=403, detail="Permisos insuficientes para acceder al panel.")
        
    # Generate token
    token = create_jwt_token({"user_id": str(user.id), "username": user.username, "role": user.role}, expires_in_seconds=7200)
    
    await log_audit(db, str(user.id), "LOGIN", f"Usuario {user.username} inició sesión en el panel.")
    
    return {
        "success": True,
        "token": token,
        "user": {
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }

# -----------------
# FAQ Admin CRUD
# -----------------
@router.get("/api/v1/admin/faqs")
async def list_faqs(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        if active_only:
            stmt = select(FAQDocument).where(FAQDocument.active == True).order_by(FAQDocument.created_at.desc())
        else:
            stmt = select(FAQDocument).order_by(FAQDocument.created_at.desc())
            
        result = await db.execute(stmt)
        docs = result.scalars().all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": str(d.id),
                    "title": d.title,
                    "content": d.content,
                    "active": d.active,
                    "priority": d.priority,
                    "qdrant_synced": d.qdrant_synced,
                    "qdrant_vector_id": d.qdrant_vector_id,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "updated_at": d.updated_at.isoformat() if d.updated_at else None
                }
                for d in docs
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list FAQs: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al listar FAQs."})

@router.post("/api/v1/admin/faqs")
async def create_faq(
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    title = payload.get("title")
    content = payload.get("content")
    keywords = payload.get("keywords", [])
    priority = payload.get("priority", 0)
    
    if not title or not content:
        raise HTTPException(status_code=400, detail="Título (pregunta) y contenido (respuesta) son requeridos.")
        
    faq_service = FAQService(db, qdrant_client)
    try:
        doc = FAQDocument(
            title=title,
            content=content,
            keywords=keywords,
            priority=priority,
            active=True,
            source="manual"
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        # Vectorize & sync with Qdrant
        synced = await faq_service.upsert_document_vector(doc)
        if synced:
            doc.qdrant_synced = True
            doc.qdrant_vector_id = str(doc.id)
            await db.commit()
            
        await log_audit(db, None, "CREATE_FAQ", f"Pregunta frecuente creada: {title}")
        
        return {
            "success": True,
            "data": {
                "id": str(doc.id),
                "title": doc.title,
                "qdrant_synced": doc.qdrant_synced
            },
            "message": "Pregunta frecuente creada con éxito."
        }
    except Exception as e:
        logger.error(f"Failed to create FAQ: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al crear la pregunta frecuente."})

@router.put("/api/v1/admin/faqs/{faq_id}")
async def update_faq(
    faq_id: uuid.UUID,
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    faq_service = FAQService(db, qdrant_client)
    try:
        stmt = select(FAQDocument).where(FAQDocument.id == faq_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Pregunta frecuente no encontrada.")
            
        # Log version history
        ver = FAQVersion(
            faq_id=doc.id,
            title=doc.title,
            content=doc.content,
            category_id=doc.category_id,
            keywords=doc.keywords,
            active=doc.active,
            priority=doc.priority
        )
        db.add(ver)
        
        # Apply updates
        doc.title = payload.get("title", doc.title)
        doc.content = payload.get("content", doc.content)
        doc.keywords = payload.get("keywords", doc.keywords)
        doc.priority = payload.get("priority", doc.priority)
        doc.active = payload.get("active", doc.active)
        doc.qdrant_synced = False
        
        await db.commit()
        await db.refresh(doc)
        
        # Re-vectorize & sync
        synced = await faq_service.upsert_document_vector(doc)
        if synced:
            doc.qdrant_synced = True
            doc.qdrant_vector_id = str(doc.id)
            await db.commit()
            
        await log_audit(db, None, "UPDATE_FAQ", f"Pregunta frecuente actualizada: {doc.title}")
        
        return {
            "success": True,
            "message": "Pregunta frecuente actualizada y re-sincronizada con Qdrant."
        }
    except Exception as e:
        logger.error(f"Failed to update FAQ {faq_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al actualizar."})

@router.delete("/api/v1/admin/faqs/{faq_id}")
async def delete_faq(
    faq_id: uuid.UUID,
    physical: bool = False,
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    faq_service = FAQService(db, qdrant_client)
    try:
        stmt = select(FAQDocument).where(FAQDocument.id == faq_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Pregunta frecuente no encontrada.")
            
        # Delete from Qdrant first
        await faq_service.delete_document_vector(faq_id)
        
        if physical:
            await db.execute(delete(FAQDocument).where(FAQDocument.id == faq_id))
            await log_audit(db, None, "PHYSICAL_DELETE_FAQ", f"Eliminación física de FAQ: {doc.title}")
        else:
            doc.active = False
            doc.qdrant_synced = False
            await log_audit(db, None, "LOGICAL_DELETE_FAQ", f"Eliminación lógica de FAQ: {doc.title}")
            
        await db.commit()
        return {"success": True, "message": "Pregunta frecuente eliminada con éxito."}
    except Exception as e:
        logger.error(f"Failed to delete FAQ {faq_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al eliminar."})

# -----------------
# History & Versioning
# -----------------
@router.get("/api/v1/admin/faqs/{faq_id}/history")
async def get_faq_history(
    faq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(FAQVersion).where(FAQVersion.faq_id == faq_id).order_by(FAQVersion.modified_at.desc())
    res = await db.execute(stmt)
    versions = res.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(v.id),
                "title": v.title,
                "content": v.content,
                "modified_at": v.modified_at.isoformat() if v.modified_at else None
            }
            for v in versions
        ]
    }

# -----------------
# Sync Actions
# -----------------
@router.post("/api/v1/admin/faqs/{faq_id}/sync")
async def sync_single_faq(
    faq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    faq_service = FAQService(db, qdrant_client)
    stmt = select(FAQDocument).where(FAQDocument.id == faq_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Pregunta frecuente no encontrada.")
        
    synced = await faq_service.upsert_document_vector(doc)
    if synced:
        doc.qdrant_synced = True
        doc.qdrant_vector_id = str(doc.id)
        await db.commit()
        return {"success": True, "message": "Sincronización exitosa."}
    return JSONResponse(status_code=500, content={"success": False, "message": "Fallo la sincronización vectorial."})

@router.post("/api/v1/admin/faqs/sync-all")
async def sync_all_faqs(
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    faq_service = FAQService(db, qdrant_client)
    try:
        # Re-create Qdrant collection to clear old points
        if qdrant_client:
            # Recreate collection
            try:
                await qdrant_client.recreate_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=qmodels.VectorParams(
                        size=1536, # text-embedding-3-small dimensions
                        distance=qmodels.Distance.COSINE
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to recreate collection: {str(e)}")
                
        stmt = select(FAQDocument).where(FAQDocument.active == True)
        res = await db.execute(stmt)
        docs = res.scalars().all()
        
        count = 0
        for doc in docs:
            synced = await faq_service.upsert_document_vector(doc)
            if synced:
                doc.qdrant_synced = True
                doc.qdrant_vector_id = str(doc.id)
                count += 1
        await db.commit()
        
        await log_audit(db, None, "SYNC_ALL_FAQS", f"Reconstruida colección Qdrant. {count} FAQs indexadas.")
        
        return {"success": True, "message": f"Sincronizados {count} registros con Qdrant."}
    except Exception as e:
        logger.error(f"Sync all failed: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al sincronizar base vectorial."})

# -----------------
# FAQ Simulation Test
# -----------------
@router.post("/api/v1/admin/faqs/test")
async def test_faq_match(
    query: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    faq_service = FAQService(db, qdrant_client)
    results = await faq_service.search_faq(query, limit=3)
    return {
        "success": True,
        "results": [
            {
                "text": r.text,
                "score": r.score,
                "category": r.category
            }
            for r in results
        ]
    }

# -----------------
# CSV Import/Export
# -----------------
@router.post("/api/v1/admin/faqs/import")
async def import_faqs_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    faq_service = FAQService(db, qdrant_client)
    try:
        contents = await file.read()
        stream = io.StringIO(contents.decode('utf-8'))
        reader = csv.DictReader(stream)
        
        count = 0
        for row in reader:
            title = row.get("pregunta") or row.get("question") or row.get("title")
            content = row.get("respuesta") or row.get("answer") or row.get("content")
            if not title or not content:
                continue
                
            doc = FAQDocument(
                title=title,
                content=content,
                keywords=[k.strip() for k in (row.get("keywords") or "").split(",") if k.strip()],
                active=True,
                priority=int(row.get("priority", 0) or 0)
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            
            # Sync vector
            synced = await faq_service.upsert_document_vector(doc)
            if synced:
                doc.qdrant_synced = True
                doc.qdrant_vector_id = str(doc.id)
                await db.commit()
            count += 1
            
        await log_audit(db, None, "IMPORT_FAQS", f"Importadas {count} FAQs desde archivo CSV.")
        return {"success": True, "message": f"Importadas {count} preguntas frecuentes con éxito."}
    except Exception as e:
        logger.error(f"Import CSV failed: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al procesar archivo CSV."})

# -----------------
# Sellers Management
# -----------------
@router.get("/api/v1/admin/sellers")
async def list_sellers(db: AsyncSession = Depends(get_db_session)):
    stmt = select(Seller).order_by(Seller.name.asc())
    res = await db.execute(stmt)
    sellers = res.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(s.id),
                "name": s.name,
                "whatsapp_phone": s.whatsapp_phone,
                "email": s.email,
                "status": s.status,
                "max_chats": s.max_chats,
                "active_chats": s.active_chats,
                "is_active": s.is_active,
                "team_zone": s.team_zone
            }
            for s in sellers
        ]
    }

@router.put("/api/v1/admin/sellers/{seller_id}")
async def update_seller(
    seller_id: uuid.UUID,
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Seller).where(Seller.id == seller_id)
    res = await db.execute(stmt)
    seller = res.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado.")
        
    seller.status = payload.get("status", seller.status)
    seller.max_chats = payload.get("max_chats", seller.max_chats)
    seller.is_active = payload.get("is_active", seller.is_active)
    await db.commit()
    
    return {"success": True, "message": f"Vendedor {seller.name} actualizado con éxito."}

# -----------------
# Supervisor/Admin Chats Monitoring
# -----------------
@router.get("/api/v1/admin/chats")
async def admin_list_chats(
    admin: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Lists all conversations in the system with their assigned seller details."""
    from app.db.tables import Conversation, Seller
    from sqlalchemy import select
    
    stmt = select(Conversation, Seller).outerjoin(
        Seller, Conversation.current_seller_id == Seller.id
    ).order_by(Conversation.last_activity_at.desc())
    
    res = await db.execute(stmt)
    rows = res.all()
    
    chats = []
    for conv, seller in rows:
        chats.append({
            "id": str(conv.id),
            "session_id": conv.session_id,
            "phone": conv.phone_hash,
            "status": conv.status,
            "last_activity": conv.last_activity_at.isoformat() if conv.last_activity_at else None,
            "assigned_seller": {
                "id": str(seller.id) if seller else None,
                "name": seller.name if seller else None,
                "email": seller.email if seller else None
            } if seller else None
        })
    return {"success": True, "data": chats}

@router.get("/api/v1/admin/chats/{conversation_id}/messages")
async def admin_get_chat_messages(
    conversation_id: uuid.UUID,
    admin: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieves all messages of any conversation for admin inspection."""
    from app.db.tables import Message
    from sqlalchemy import select
    
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

@router.post("/api/v1/admin/chats/{conversation_id}/messages")
async def admin_send_message(
    conversation_id: uuid.UUID,
    content: str = Body(..., embed=True),
    admin: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
    redis_client = Depends(get_redis)
):
    """Allows admin/supervisor to send a manual outbound message directly, pausing bot."""
    from app.db.tables import Conversation, Message
    import httpx
    import datetime
    import json
    
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        
    conv.status = "human_active"
    
    new_msg = Message(
        conversation_id=conversation_id,
        direction="outbound",
        role="seller",
        content=f"[Supervisor] {content}",
        message_type="text"
    )
    db.add(new_msg)
    await db.commit()
    
    raw_phone = await redis_client.get(f"phone_map:{conv.phone_hash}")
    if not raw_phone:
        raw_phone = conv.phone_hash
        
    sent = False
    try:
        headers = {
            "X-Internal-API-Key": settings.INTERNAL_API_KEY,
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://whatsapp-gateway:8090/send",
                json={"phone": raw_phone, "message": content},
                headers=headers,
                timeout=10.0
            )
            if resp.status_code == 200:
                sent = True
    except Exception as e:
        logger.error(f"Admin fail to post to gateway: {e}")
        
    payload = {
        "type": "new_message",
        "data": {
            "conversation_id": str(conversation_id),
            "direction": "outbound",
            "role": "seller",
            "content": f"[Supervisor] {content}",
            "created_at": datetime.datetime.utcnow().isoformat()
        }
    }
    await redis_client.publish("seller_updates", json.dumps(payload))
    
    return {"success": sent, "message": "Mensaje enviado por el supervisor."}
