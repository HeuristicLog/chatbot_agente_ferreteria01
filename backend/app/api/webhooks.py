"""
WhatsApp Webhook Router — Interactive Flow Engine
Handles both text messages and interactive button/list replies.
Routes to guided flows or Flowise AI for free-text questions.
"""
import logging
import httpx
import json
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.db.session import get_db_session
from app.dependencies import get_redis, verify_internal_auth
from app.domain.models import IncomingWhatsAppMessage
from app.db.tables import Message as DBMessage
from app.services.session_service import SessionService
from app.services.audit_service import AuditService
from app.services.flowise_service import FlowiseService
from app.security.sanitization import sanitize_user_input
from app.config import settings
from app.services.chatwoot_service import ChatwootService
import app.services.interactive_flow_service as flows

logger = logging.getLogger("chatbot-api.api.webhooks")
router = APIRouter()

GATEWAY_URL = "http://whatsapp-gateway:8090"
internal_api_key = settings.INTERNAL_API_KEY

# ─── Rate Limiting ─────────────────────────────────────────────

async def check_rate_limit(redis_client: redis.Redis, session_id: str) -> bool:
    limit = int(settings.RATE_LIMIT_MESSAGES_PER_MINUTE or 20)
    key = f"rate_limit:{session_id}"
    current = await redis_client.get(key)
    if current and int(current) >= limit:
        return False
    async with redis_client.pipeline(transaction=True) as pipe:
        await pipe.incr(key)
        await pipe.expire(key, 60)
        await pipe.execute()
    return True

# ─── Flow State (Redis) ────────────────────────────────────────

async def get_flow_state(redis_client: redis.Redis, phone: str) -> dict:
    raw = await redis_client.get(f"flow_state:{phone}")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}

async def set_flow_state(redis_client: redis.Redis, phone: str, state: dict, ttl: int = 600):
    await redis_client.set(f"flow_state:{phone}", json.dumps(state), ex=ttl)

async def clear_flow_state(redis_client: redis.Redis, phone: str):
    await redis_client.delete(f"flow_state:{phone}")

# ─── Save helpers ──────────────────────────────────────────────

async def save_message(db: AsyncSession, conv_id, direction: str, role: str, content: str, msg_id: str = None):
    msg = DBMessage(
        conversation_id=conv_id,
        direction=direction,
        role=role,
        content=content,
        message_type="text",
        external_message_id=msg_id
    )
    db.add(msg)
    await db.commit()

# ─── Send helpers (fire-and-forget) ──────────────────────────

async def _gateway_send_text(phone: str, message: str, phone_number_id: Optional[str] = None, access_token: Optional[str] = None, sync_to_chatwoot: bool = True):
    # Sincronizar salida del bot con Chatwoot
    if sync_to_chatwoot:
        try:
            chatwoot = ChatwootService()
            if chatwoot.is_configured:
                await chatwoot.post_bot_message(phone, message, phone_number_id)
        except Exception as cw_err:
            logger.error(f"Error sincronizando salida de texto del bot con Chatwoot: {cw_err}")

    headers = {"X-Internal-API-Key": internal_api_key}
    payload = {"phone": phone, "message": message}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
    if access_token:
        payload["access_token"] = access_token
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{GATEWAY_URL}/send", json=payload, headers=headers, timeout=10.0)
    except Exception as e:
        logger.error(f"Gateway send_text error: {e}")

# ─── MAIN WEBHOOK ──────────────────────────────────────────────

@router.post("/webhooks/whatsapp", dependencies=[Depends(verify_internal_auth)])
async def receive_incoming_message(
    payload: IncomingWhatsAppMessage,
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    session_service = SessionService(db, redis_client)
    flowise_service = FlowiseService()

    dest_phone_number_id = payload.metadata.get("phone_number_id")
    session_id = session_service.derive_session_id(payload.phone, dest_phone_number_id)
    logger.info(f"Message from {payload.phone} (phone_number_id: {dest_phone_number_id}) → session {session_id}")

    # Rate limit
    if not await check_rate_limit(redis_client, session_id):
        raise HTTPException(status_code=429, detail="Límite de mensajes excedido.")

    # Get or create conversation
    conv = await session_service.get_or_create_conversation(
        payload.phone, provider=payload.metadata.get("provider", "mock"), phone_number_id=dest_phone_number_id
    )

    # Cache phone hash
    phone_hash = session_service.derive_phone_hash(payload.phone)
    await redis_client.set(f"phone_map:{phone_hash}", payload.phone)

    # Idempotency check
    msg_id_key = f"msg_id:{payload.message_id}"
    if await redis_client.get(msg_id_key):
        return {"status": "duplicate"}
    await redis_client.set(msg_id_key, "1", ex=3600)

    sanitized = sanitize_user_input(payload.message)

    # ── Sincronizar mensaje entrante con Chatwoot (desde el inicio) ──
    chatwoot = ChatwootService()
    cw_conv_id = None
    if chatwoot.is_configured:
        try:
            inbox_id = None
            from app.config import settings
            mapping = settings.whatsapp_inbox_mapping or {}
            if dest_phone_number_id and dest_phone_number_id in mapping:
                inbox_id = mapping[dest_phone_number_id].get("inbox_id")
            
            cw_contact_id = await chatwoot.get_or_create_contact(payload.phone, f"Cliente +{payload.phone}", inbox_id=inbox_id)
            if cw_contact_id:
                cw_conv_id = await chatwoot.get_or_create_conversation(cw_contact_id, inbox_id=inbox_id)
                if cw_conv_id:
                    await chatwoot.post_message(cw_conv_id, sanitized, message_type="incoming")
                    # Mantener silenciada la conversación si el bot está activo
                    if conv.status == "bot_active":
                        await chatwoot.update_conversation_status(cw_conv_id, "snoozed")
        except Exception as cw_err:
            logger.error(f"Error sincronizando mensaje entrante con Chatwoot: {cw_err}")

    # ── 1. Active Handoff Lock ─────────────────────────────────
    if conv.status in ["waiting_agent", "assigned", "human_active", "handed_over"]:
        await save_message(db, conv.id, "inbound", "user", sanitized, payload.message_id)
        event = {"type": "new_message", "data": {"conversation_id": str(conv.id), "direction": "inbound", "role": "user", "content": sanitized}}
        await redis_client.publish("seller_updates", json.dumps(event))

        if conv.status == "waiting_agent":
            reply = "Tu solicitud sigue en espera. ✋ Pronto un asesor te atenderá. Gracias por tu paciencia."
            target_access_token = None
            from app.config import settings
            mapping = settings.whatsapp_inbox_mapping or {}
            if dest_phone_number_id and dest_phone_number_id in mapping:
                target_access_token = mapping[dest_phone_number_id].get("access_token")
            await _gateway_send_text(payload.phone, reply, phone_number_id=dest_phone_number_id, access_token=target_access_token)
            await save_message(db, conv.id, "outbound", "assistant", reply)
        return {"status": "handoff_bypass"}

    # ── 2. Interactive Reply Routing ───────────────────────────
    interactive_id = payload.metadata.get("interactive_id", "")

    if interactive_id:
        logger.info(f"Interactive reply: id={interactive_id} text={sanitized}")
        await save_message(db, conv.id, "inbound", "user", sanitized, payload.message_id)

        # ── Menu principal
        if interactive_id in ["menu_inicio", "menu_main"]:
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_main_menu(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Menú principal enviado")
            return {"status": "processed"}

        # ── Flujo: Catálogo Emergente en WhatsApp (CTA URL Webview)
        if interactive_id == "flow_catalogo":
            await clear_flow_state(redis_client, payload.phone)
            suc_name = "Centro"
            if dest_phone_number_id and dest_phone_number_id in (settings.whatsapp_inbox_mapping or {}):
                suc_name = settings.whatsapp_inbox_mapping[dest_phone_number_id].get("sucursal", "Centro")
            await flows.send_catalog_link(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id, sucursal=suc_name)
            await save_message(db, conv.id, "outbound", "assistant", "Tarjeta de catálogo emergente enviada")
            return {"status": "processed"}

        # ── Catálogo: Categorías
        if interactive_id.startswith("cat_"):
            await clear_flow_state(redis_client, payload.phone)
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.send_products_in_category(payload.phone, interactive_id, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Catálogo: Ver Producto Detalle
        if interactive_id.startswith("prod_view_"):
            await clear_flow_state(redis_client, payload.phone)
            sku = interactive_id.replace("prod_view_", "")
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.send_product_detail(payload.phone, sku, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Carrito: Agregar Item
        if interactive_id.startswith("cart_add_"):
            parts = interactive_id.split("_")
            sku = parts[2]
            qty = int(parts[3]) if len(parts) > 3 else 1
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.handle_add_to_cart(payload.phone, sku, qty, redis_client, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Carrito: Ver Carrito
        if interactive_id == "cart_view":
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.send_cart_view(payload.phone, redis_client, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Carrito: Vaciar Carrito
        if interactive_id == "cart_clear":
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.clear_cart(redis_client, payload.phone)
            await in_chat_cart.send_cart_view(payload.phone, redis_client, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Checkout: Iniciar Pedido
        if interactive_id == "checkout_start":
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.prompt_delivery_method(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Checkout: Retiro en Sucursal
        if interactive_id == "order_pickup":
            from app.services import in_chat_cart_service as in_chat_cart
            cart = await in_chat_cart.get_cart(redis_client, payload.phone)
            cart["delivery_type"] = "pickup"
            await in_chat_cart.save_cart(redis_client, payload.phone, cart)
            await in_chat_cart.prompt_sucursal_selection(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Checkout: Selección de Sucursal
        if interactive_id.startswith("order_suc_"):
            from app.services import in_chat_cart_service as in_chat_cart
            suc_map = {
                "order_suc_centro": "Centro",
                "order_suc_norte": "Norte",
                "order_suc_sur": "Sur",
                "order_suc_cumbaya": "Cumbayá"
            }
            cart = await in_chat_cart.get_cart(redis_client, payload.phone)
            cart["sucursal"] = suc_map.get(interactive_id, "Centro")
            await in_chat_cart.save_cart(redis_client, payload.phone, cart)
            await in_chat_cart.prompt_payment_method(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Checkout: Envío a Domicilio
        if interactive_id == "order_delivery":
            from app.services import in_chat_cart_service as in_chat_cart
            cart = await in_chat_cart.get_cart(redis_client, payload.phone)
            cart["delivery_type"] = "delivery"
            await in_chat_cart.save_cart(redis_client, payload.phone, cart)
            await set_flow_state(redis_client, payload.phone, {"flow": "cart_delivery", "step": "waiting_address"})
            await flows._send(
                payload.phone,
                "📍 Por favor escribe tu dirección exacta de entrega en este chat (ej. *Av. 10 de Agosto y Colón, Edif. 4*):",
                internal_api_key,
                phone_number_id=dest_phone_number_id
            )
            return {"status": "processed"}

        # ── Checkout: Método de Pago y Finalizar
        if interactive_id.startswith("pay_"):
            method = interactive_id.replace("pay_", "")
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.complete_in_chat_order(
                payload.phone, redis_client, db, method, internal_api_key, phone_number_id=dest_phone_number_id
            )
            return {"status": "processed"}

        # ── Flujo: Estado de pedido
        if interactive_id == "flow_pedido":
            await set_flow_state(redis_client, payload.phone, {"flow": "order_status", "step": "waiting_id"})
            await flows.send_order_status_request(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Flujo: Mis tickets
        if interactive_id == "flow_ticket":
            await set_flow_state(redis_client, payload.phone, {"flow": "ticket_status", "step": "waiting_id"})
            await flows.send_ticket_request(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Flujo: FAQ lista
        if interactive_id == "flow_faq":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_faq_list(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── FAQ específica
        if interactive_id.startswith("faq_"):
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_faq_answer(payload.phone, interactive_id, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Flujo: Asesor (pedir confirmación)
        if interactive_id == "flow_asesor":
            await flows.send_advisor_confirmation(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # ── Confirmar transferencia a asesor por sucursal
        if interactive_id.startswith("confirm_asesor_"):
            suc_key = interactive_id.replace("confirm_asesor_", "")
            suc_map = {
                "norte": "Norte",
                "centro": "Centro",
                "sur": "Sur",
                "cumbaya": "Cumbayá"
            }
            suc_name = suc_map.get(suc_key, suc_key.capitalize())
            await _do_handoff(payload.phone, conv, db, redis_client, flowise_service, session_id, sucursal=suc_name, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

    # ── 3. Text Flow State Machine ─────────────────────────────
    flow_state = await get_flow_state(redis_client, payload.phone)
    await save_message(db, conv.id, "inbound", "user", sanitized, payload.message_id)

    if flow_state:
        flow = flow_state.get("flow")
        step = flow_state.get("step")

        # Waiting for order ID
        if flow == "order_status" and step == "waiting_id":
            await clear_flow_state(redis_client, payload.phone)
            await flows.handle_order_result(
                payload.phone, sanitized, internal_api_key, redis_client, phone_number_id=dest_phone_number_id
            )
            return {"status": "processed"}

        # Waiting for delivery address
        if flow == "cart_delivery" and step == "waiting_address":
            from app.services import in_chat_cart_service as in_chat_cart
            cart = await in_chat_cart.get_cart(redis_client, payload.phone)
            cart["address"] = sanitized
            await in_chat_cart.save_cart(redis_client, payload.phone, cart)
            await clear_flow_state(redis_client, payload.phone)
            await in_chat_cart.prompt_payment_method(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            return {"status": "processed"}

        # Waiting for ticket ID
        if flow == "ticket_status" and step == "waiting_id":
            await clear_flow_state(redis_client, payload.phone)
            await flows.handle_ticket_result(
                payload.phone, sanitized, internal_api_key, redis_client, phone_number_id=dest_phone_number_id
            )
            return {"status": "processed"}

    # ── 4. Intent & Keyword Routing ───────────────────────────
    clean_msg = sanitized.lower().strip()

    # Saludos
    greeting_words = ["hola", "hi", "hello", "buenas", "buenos", "hey", "buen dia", "buenos dias", "inicio", "start", "menu", "menú"]
    if any(clean_msg.startswith(g) or clean_msg == g for g in greeting_words):
        await clear_flow_state(redis_client, payload.phone)
        await flows.send_welcome_menu(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Menú de bienvenida enviado")
        return {"status": "processed"}

    # Catálogo / Productos / Carrito Emergente en WhatsApp
    catalog_keywords = ["catalogo", "catálogo", "productos", "inventario", "precios", "tienda", "carrito", "comprar", "lista de productos"]
    if any(k in clean_msg for k in catalog_keywords):
        await clear_flow_state(redis_client, payload.phone)
        suc_name = "Centro"
        if dest_phone_number_id and dest_phone_number_id in (settings.whatsapp_inbox_mapping or {}):
            suc_name = settings.whatsapp_inbox_mapping[dest_phone_number_id].get("sucursal", "Centro")
        await flows.send_catalog_link(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id, sucursal=suc_name)
        await save_message(db, conv.id, "outbound", "assistant", "Tarjeta de catálogo emergente enviada")
        return {"status": "processed"}

    # Código de Pedido directo (ej. CAST-2026-1024 o OP-101)
    if clean_msg.startswith("cast-") or clean_msg.startswith("op-") or clean_msg.startswith("#cast-") or clean_msg.startswith("#op-"):
        await clear_flow_state(redis_client, payload.phone)
        await flows.handle_order_result(payload.phone, sanitized, internal_api_key, redis_client, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", f"Consulta de pedido {sanitized}")
        return {"status": "processed"}

    # ── 5. Free-text → Flowise AI ─────────────────────────────
    ai_response = await flowise_service.get_prediction(sanitized, session_id, phone=payload.phone)
    await save_message(db, conv.id, "outbound", "assistant", ai_response)

    # Enviar respuesta IA con botones de navegación
    await flows.send_ai_response_with_menu(payload.phone, ai_response, internal_api_key, phone_number_id=dest_phone_number_id)
    return {"status": "processed", "session_id": session_id}


async def _do_handoff(phone: str, conv, db, redis_client, flowise_service: FlowiseService, session_id: str, sucursal: Optional[str] = None, phone_number_id: Optional[str] = None):
    """Ejecuta la transferencia a asesor humano."""
    try:
        reason = f"Solicitud del usuario (Sucursal: {sucursal})" if sucursal else "Solicitud del usuario"
        summary = f"El cliente solicitó hablar con un asesor de la sucursal {sucursal or 'no especificada'} desde el menú interactivo."
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://backend:8080/tools/handoff?session_id={session_id}",
                json={"session_id": session_id, "phone": phone, "reason": reason, "summary": summary, "sucursal": sucursal, "phone_number_id": phone_number_id},
                timeout=10.0
            )
        if resp.status_code == 200:
            return  # HandoffService already sent the appropriate welcome/queue message to the client
            
        msg = "⚠️ No pudimos conectarte en este momento. Por favor intenta más tarde o llámanos directamente."
        
        target_access_token = None
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id and phone_number_id in mapping:
            target_access_token = mapping[phone_number_id].get("access_token")
        await _gateway_send_text(phone, msg, phone_number_id=phone_number_id, access_token=target_access_token)
        db_msg = DBMessage(conversation_id=conv.id, direction="outbound", role="assistant", content=msg, message_type="text")
        db.add(db_msg)
        await db.commit()
    except Exception as e:
        logger.error(f"Handoff error: {e}")
        target_access_token = None
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id and phone_number_id in mapping:
            target_access_token = mapping[phone_number_id].get("access_token")
        await _gateway_send_text(phone, "⚠️ Error al conectar con el asesor. Intenta nuevamente.", phone_number_id=phone_number_id, access_token=target_access_token)


@router.post("/webhooks/chatwoot")
async def chatwoot_webhook(
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    redis_client = Depends(get_redis)
):
    """Webhook para recibir respuestas desde Chatwoot y reenviarlas a WhatsApp."""
    logger.info(f"Chatwoot Webhook Payload received: {payload}")
    event = payload.get("event")
    message_type = payload.get("message_type")
    is_private = payload.get("private", False)

    if event == "message_created" and message_type == "outgoing" and not is_private:
        msg_id = payload.get("id")
        if msg_id:
            lock_key = f"cw_msg_id:{msg_id}"
            is_new = await redis_client.set(lock_key, "1", ex=300, nx=True)
            if not is_new:
                logger.info(f"Ignorando duplicado de webhook Chatwoot para mensaje {msg_id}")
                return {"status": "duplicate"}

        # Evitar bucles: Solo reenviar si el mensaje fue escrito por un agente humano
        sender = payload.get("sender")
        if not isinstance(sender, dict) or sender.get("type") != "user":
            logger.info("Ignorando mensaje saliente automático/bot para evitar bucle recursivo.")
            return {"status": "ignored_loop_prevention"}

        content = payload.get("content")
        conversation = payload.get("conversation", {})
        inbox_id = conversation.get("inbox_id")
        
        # Reverse lookup phone_number_id and access_token based on Chatwoot inbox_id
        target_phone_number_id = None
        target_access_token = None
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        for pid, mapping_info in mapping.items():
            if mapping_info.get("inbox_id") == inbox_id:
                target_phone_number_id = pid
                target_access_token = mapping_info.get("access_token")
                break

        # Obtener el número de teléfono del cliente de forma robusta
        phone = conversation.get("meta", {}).get("sender", {}).get("phone_number")
        if not phone:
            contact_inbox = conversation.get("contact_inbox", {})
            if isinstance(contact_inbox, dict):
                contact = contact_inbox.get("contact", {})
                if isinstance(contact, dict):
                    phone = contact.get("phone_number")
        if not phone:
            meta = payload.get("meta", {})
            sender = meta.get("sender", {}) if isinstance(meta, dict) else {}
            phone = sender.get("phone_number") if isinstance(sender, dict) else None

        if phone and content:
            # Limpiar el formato de teléfono (+593... -> 593...)
            clean_phone = phone.replace("+", "").strip()

            # Evitar bucles recursivos: Si la sesión está en estado bot_active o active, no reenviar.
            try:
                from app.services.session_service import SessionService
                session_id = SessionService.derive_session_id(clean_phone, target_phone_number_id)
                from app.repositories.conversation_repository import ConversationRepository
                repo = ConversationRepository(db)
                conv = await repo.get_by_session_id(session_id)
                if conv and conv.status in ["active", "bot_active"]:
                    logger.info(f"Ignorando reenvío de Chatwoot a WhatsApp para {clean_phone} porque la sesión {session_id} está en estado {conv.status} (chatbot activo).")
                    return {"status": "ignored_chatbot_active"}
            except Exception as check_err:
                logger.error(f"Error verificando estado de la conversación para evitar bucles: {check_err}")

            logger.info(f"Reenvío de Chatwoot a WhatsApp ({clean_phone}, inbox: {inbox_id}, phone_number_id: {target_phone_number_id}): {content[:50]}...")

            try:
                # Enviar vía gateway con credenciales específicas de la sucursal
                await _gateway_send_text(clean_phone, content, phone_number_id=target_phone_number_id, access_token=target_access_token, sync_to_chatwoot=False)

                # Registrar mensaje localmente
                from app.services.session_service import SessionService
                from app.repositories.conversation_repository import ConversationRepository
                from app.db.tables import Conversation, Message as DBMessage
                from sqlalchemy import select

                conv_repo = ConversationRepository(db)
                session_service = SessionService(db, redis_client)
                phone_hash = session_service.derive_phone_hash(clean_phone)

                stmt = select(Conversation).where(Conversation.phone_hash == phone_hash).order_by(Conversation.last_activity_at.desc())
                res = await db.execute(stmt)
                conv = res.scalars().first()

                if conv:
                    db_msg = DBMessage(
                        conversation_id=conv.id,
                        direction="outbound",
                        role="seller",
                        content=content,
                        message_type="text"
                    )
                    db.add(db_msg)
                    await db.commit()
            except Exception as e:
                logger.error(f"Error reenviando mensaje de Chatwoot a WhatsApp: {e}")

    elif event == "conversation_status_changed":
        conversation = payload.get("conversation")
        if not isinstance(conversation, dict):
            conversation = payload
            
        status = conversation.get("status")

        if status == "resolved":
            inbox_id = conversation.get("inbox_id")
            
            # Reverse lookup phone_number_id and access_token based on Chatwoot inbox_id
            target_phone_number_id = None
            target_access_token = None
            from app.config import settings
            mapping = settings.whatsapp_inbox_mapping or {}
            for pid, mapping_info in mapping.items():
                if mapping_info.get("inbox_id") == inbox_id:
                    target_phone_number_id = pid
                    target_access_token = mapping_info.get("access_token")
                    break

            contact = conversation.get("contact")
            phone = contact.get("phone_number") if isinstance(contact, dict) else None
            if not phone:
                meta = conversation.get("meta", {})
                if isinstance(meta, dict):
                    sender = meta.get("sender", {})
                    if isinstance(sender, dict):
                        phone = sender.get("phone_number")

            if phone:
                clean_phone = phone.replace("+", "").strip()
                logger.info(f"Conversación de Chatwoot resuelta para el cliente ({clean_phone}). Reactivando el bot...")

                try:
                    from app.services.session_service import SessionService
                    from app.repositories.conversation_repository import ConversationRepository
                    from app.db.tables import Conversation, Message as DBMessage
                    from sqlalchemy import select

                    conv_repo = ConversationRepository(db)
                    session_service = SessionService(db, redis_client)
                    phone_hash = session_service.derive_phone_hash(clean_phone)

                    stmt = select(Conversation).where(Conversation.phone_hash == phone_hash).order_by(Conversation.last_activity_at.desc())
                    res = await db.execute(stmt)
                    conv = res.scalars().first()

                    if conv:
                        conv.status = "bot_active"
                        db.add(conv)

                        # Resolve active handoffs in local database
                        from app.repositories.audit_repository import AuditRepository
                        audit_repo = AuditRepository(db)
                        active_handoff = await audit_repo.get_active_handoff(conv.id)
                        if active_handoff:
                            await audit_repo.resolve_handoff(active_handoff.id, "Chatwoot Agent")

                        await redis_client.delete(f"flow_state:{clean_phone}")

                        msg = "✅ *Atención al cliente finalizada.* El asistente virtual Castor vuelve a estar activo. Escribe *hola* para ver el menú principal."
                        await _gateway_send_text(clean_phone, msg, phone_number_id=target_phone_number_id, access_token=target_access_token)

                        db_msg = DBMessage(
                            conversation_id=conv.id,
                            direction="outbound",
                            role="assistant",
                            content=msg,
                            message_type="text"
                        )
                        db.add(db_msg)
                        await db.commit()
                except Exception as e:
                    logger.error(f"Error reactivando el bot tras resolución de Chatwoot: {e}")

    return {"status": "ok"}
