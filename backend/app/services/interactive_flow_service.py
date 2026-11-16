"""
Interactive Flow Service
Motor de flujos conversacionales interactivos para WhatsApp.
Gestiona menús con botones, listas de selección y flujos guiados multi-paso.
"""
import logging
import httpx
import json
from typing import Optional, Dict, Any

from app.services.auth_service import LogisticsAuthService
from app.services.logistic_operation_service import LogisticOperationService
from app.services.ticket_service import TicketService

logger = logging.getLogger("chatbot-api.services.interactive_flow")

GATEWAY_URL = "http://whatsapp-gateway:8090"

EVOLUTION_CANDIDATE_URLS = [
    "http://evolution-api:8080",
    "http://autoeconomotors-evolution:8080",
    "http://10.10.10.29:8082",
    "http://host.docker.internal:8082",
    "http://localhost:8082"
]

_working_evo_url = None

async def _save_db_message(phone: str, content: str, role: str = "assistant", direction: str = "outbound", msg_type: str = "text"):
    """Persiste inmediatamente el mensaje en la tabla chatbot_messages de PostgreSQL para auditoría completa."""
    try:
        from app.db.session import async_session
        from app.db.tables import Conversation as DBConversation, Message as DBMessage
        from sqlalchemy import select, func
        clean_p = phone.replace("+", "").replace(" ", "").strip()
        
        async with async_session() as db:
            stmt = select(DBConversation).where(
                DBConversation.phone_hash.like(f"%{clean_p}%")
            ).order_by(DBConversation.last_activity_at.desc()).limit(1)
            result = await db.execute(stmt)
            conv = result.scalar_one_or_none()
            if not conv:
                conv = DBConversation(
                    session_id=f"evo_{clean_p}",
                    phone_hash=clean_p,
                    provider="evolution",
                    status="bot_active"
                )
                db.add(conv)
                await db.flush()
            
            db_msg = DBMessage(
                conversation_id=conv.id,
                direction=direction,
                role=role,
                content=content,
                message_type=msg_type
            )
            db.add(db_msg)
            conv.last_activity_at = func.now()
            await db.commit()
    except Exception as db_err:
        logger.debug(f"Error guardando mensaje en PostgreSQL: {db_err}")

async def _send_evolution_text(phone: str, text: str, instance: Optional[str] = None, phone_number_id: Optional[str] = None) -> bool:
    """Envía mensajes formateados directamente a través de Evolution API (WhatsApp QR Baileys) con protección de eco."""
    global _working_evo_url
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    
    target_inst = instance
    if not target_inst and phone_number_id:
        if str(phone_number_id) in ["593992451085", "151924"]:
            target_inst = "bonilla_1085"
        elif str(phone_number_id) in ["593988921136", "150556"]:
            target_inst = "sucursal_centro"

    if not target_inst:
        try:
            import redis.asyncio as aioredis
            import os
            r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            rc = aioredis.from_url(r_url)
            inst_bytes = await rc.get(f"user_instance:{clean_p}")
            if inst_bytes:
                target_inst = inst_bytes.decode('utf-8') if isinstance(inst_bytes, bytes) else str(inst_bytes)
            await rc.aclose()
        except Exception:
            pass

    if not target_inst:
        target_inst = "bonilla_1085" if "992451085" in clean_p else "sucursal_centro"

    # Marcar firma del mensaje en Redis ANTES de enviarlo para que cuando Baileys emita el fromMe no lo tome como mensaje humano
    import hashlib
    norm_t = text.strip()
    msg_sig = hashlib.md5(f"{clean_p}:{norm_t}".encode()).hexdigest()
    try:
        import redis.asyncio as aioredis
        import os
        r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        rc = aioredis.from_url(r_url)
        await rc.set(f"cw_to_evo:{msg_sig}", "1", ex=180)
        await rc.set(f"bot_sent:{msg_sig}", "1", ex=180)
        await rc.aclose()
    except Exception:
        pass

    headers = {"apikey": "ferreteria_evolution_key_2026"}
    
    candidates = list(EVOLUTION_CANDIDATE_URLS)
    if _working_evo_url and _working_evo_url in candidates:
        candidates.remove(_working_evo_url)
        candidates.insert(0, _working_evo_url)

    for base in candidates:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{base}/message/sendText/{target_inst}",
                    json={"number": clean_p, "text": text},
                    headers=headers
                )
                if resp.status_code in [200, 201]:
                    _working_evo_url = base
                    # También guardar el key.id que devuelve Evolution para deduplicación exacta
                    try:
                        evo_resp_data = resp.json()
                        evo_msg_id = evo_resp_data.get("key", {}).get("id") if isinstance(evo_resp_data, dict) else None
                        if evo_msg_id:
                            rc = aioredis.from_url(r_url)
                            await rc.set(f"cw_to_evo:{evo_msg_id}", "1", ex=180)
                            await rc.set(f"bot_sent:{evo_msg_id}", "1", ex=180)
                            await rc.aclose()
                    except Exception:
                        pass
                    logger.info(f"Mensaje despachado via Evolution API ({base}/{target_inst}) a {clean_p}")
                    return True
                else:
                    logger.warning(f"Evolution API ({base}/{target_inst}) devolvió {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.debug(f"Error conectando a Evolution API {base}: {e}")
            continue
    return False

# ─────────────────────────────────────────────
# HELPERS — Enviar mensajes al Gateway / Evolution
# ─────────────────────────────────────────────

async def _send(phone: str, message: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Envía un mensaje de texto simple y lo guarda en base de datos."""
    # Persistir en base de datos
    await _save_db_message(phone, message)

    # Sincronizar salida de texto del bot con Chatwoot
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            await chatwoot.post_bot_message(phone, message, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando salida de texto del bot con Chatwoot en _send: {cw_err}")

    # 1. Intentar despacho directo por Evolution API (WhatsApp Baileys QR)
    if await _send_evolution_text(phone, message, phone_number_id=phone_number_id):
        return

    # 2. Fallback a WhatsApp Gateway (Meta Cloud API)
    headers = {"X-Internal-API-Key": internal_key}
    payload = {"phone": phone, "message": message}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")
            
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{GATEWAY_URL}/send",
                json=payload,
                headers=headers,
                timeout=10.0
            )
    except Exception as e:
        logger.debug(f"Gateway send fallback error: {e}")

async def _send_buttons(phone: str, body: str, buttons: list, header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje con opciones numeradas limpias e interactivas sin IDs técnicos visibles."""
    clean_p = phone.replace("+", "").replace(" ", "").strip()

    # Formatear opciones numeradas con emojis limpios (NUNCA mostrar flow_faq o IDs técnicos)
    btn_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    btn_lines = []
    
    # Guardar en Redis mapeo temporal: botón digitado (1, 2, 3) -> ID de acción
    try:
        import redis.asyncio as aioredis
        import os
        r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        rc = aioredis.from_url(r_url)
        for idx, b in enumerate(buttons):
            act_id = b.get("id", str(idx+1))
            await rc.set(f"btn_opt:{clean_p}:{idx+1}", act_id, ex=900)
            clean_title = (b.get("title", "")).lower()
            await rc.set(f"btn_title:{clean_p}:{clean_title}", act_id, ex=900)
        await rc.aclose()
    except Exception:
        pass

    for idx, b in enumerate(buttons):
        emoji_num = btn_numbers[idx] if idx < len(btn_numbers) else f"{idx+1}️⃣"
        btn_lines.append(f"{emoji_num} *{b.get('title')}*")

    parts = []
    if header:
        parts.append(f"*{header}*")
    parts.append(body)
    if btn_lines:
        parts.append("\n".join(btn_lines))
    
    prompt_footer = footer or "Responde con el número de tu opción (1, 2 o 3)"
    parts.append(f"_{prompt_footer}_")
    formatted_msg = "\n\n".join(parts)

    # Persistir en base de datos PostgreSQL
    await _save_db_message(phone, formatted_msg)

    # Sincronizar botones del bot con Chatwoot
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            await chatwoot.post_bot_message(phone, formatted_msg, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando botones del bot con Chatwoot en _send_buttons: {cw_err}")

    # Despacho por Evolution API
    if await _send_evolution_text(phone, formatted_msg, phone_number_id=phone_number_id):
        return

    # Fallback a Gateway Meta Cloud API
    headers = {"X-Internal-API-Key": internal_key}
    payload = {"phone": phone, "body": body, "buttons": buttons, "header": header, "footer": footer}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{GATEWAY_URL}/send/buttons",
                json=payload,
                headers=headers,
                timeout=10.0
            )
    except Exception as e:
        logger.debug(f"Gateway send_buttons fallback error: {e}")

async def _send_list(phone: str, body: str, button_text: str, sections: list, header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje con lista de opciones numeradas y limpias."""
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    sec_lines = []
    opt_idx = 1
    
    # Guardar en Redis mapeo temporal (opción digitada -> ID de categoría o producto)
    try:
        import redis.asyncio as aioredis
        import os
        r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        rc = aioredis.from_url(r_url)
        for sec in sections:
            if sec.get('title'):
                sec_lines.append(f"📋 *{sec.get('title')}*")
            for row in sec.get('rows', []):
                desc = f" — _{row.get('description')}_" if row.get('description') else ""
                row_id = row.get('id', str(opt_idx))
                await rc.set(f"btn_opt:{clean_p}:{opt_idx}", row_id, ex=900)
                sec_lines.append(f"*{opt_idx}.* {row.get('title')}{desc}")
                opt_idx += 1
        await rc.aclose()
    except Exception:
        pass

    parts = []
    if header:
        parts.append(f"*{header}*")
    parts.append(body)
    if sec_lines:
        parts.append("\n".join(sec_lines))
    
    prompt_footer = footer or "Escribe el número de la opción deseada"
    parts.append(f"_{prompt_footer}_")
    formatted_msg = "\n\n".join(parts)

    # Persistir en base de datos PostgreSQL
    await _save_db_message(phone, formatted_msg)

    # Sincronizar listas del bot con Chatwoot
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            await chatwoot.post_bot_message(phone, formatted_msg, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando lista del bot con Chatwoot en _send_list: {cw_err}")

    if await _send_evolution_text(phone, formatted_msg, phone_number_id=phone_number_id):
        return

    # Fallback a Gateway Meta Cloud API
    headers = {"X-Internal-API-Key": internal_key}
    payload = {"phone": phone, "body": body, "button_text": button_text, "sections": sections, "header": header, "footer": footer}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{GATEWAY_URL}/send/list",
                json=payload,
                headers=headers,
                timeout=10.0
            )
    except Exception as e:
        logger.debug(f"Gateway send_list fallback error: {e}")

async def _send_cta_url(phone: str, body: str, display_text: str, url: str, header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje interactivo con enlace clickeable directo y previsualización."""
    # Para Evolution API (WhatsApp Baileys QR), enviar con enlace clickeable directo
    parts = []
    if header:
        parts.append(f"*{header}*")
    parts.append(body)
    parts.append(f"👉 *{display_text}:*\n{url}")
    if footer:
        parts.append(f"_{footer}_")
    formatted_msg = "\n\n".join(parts)

    # Persistir en base de datos PostgreSQL
    await _save_db_message(phone, formatted_msg)

    # Sincronizar CTA URL con Chatwoot
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            await chatwoot.post_bot_message(phone, formatted_msg, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando CTA URL con Chatwoot: {cw_err}")

    if await _send_evolution_text(phone, formatted_msg, phone_number_id=phone_number_id):
        return

    # 2. Fallback a Gateway Meta Cloud API
    headers = {"X-Internal-API-Key": internal_key}
    payload = {
        "phone": phone,
        "body": body,
        "display_text": display_text,
        "url": url,
        "header": header,
        "footer": footer
    }
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{GATEWAY_URL}/send/cta_url",
                json=payload,
                headers=headers,
                timeout=10.0
            )
    except Exception as e:
        logger.debug(f"Gateway send_cta_url fallback error: {e}")

async def _send_flow(phone: str, body: str, flow_id: str, flow_cta: str, flow_token: str = "token_01", screen: str = "CATALOG_SCREEN", header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None) -> bool:
    """Envía mensaje interactivo con WhatsApp Flow oficial de Meta (pantalla emergente nativa)."""
    headers = {"X-Internal-API-Key": internal_key}
    payload = {
        "phone": phone,
        "body": body,
        "flow_id": flow_id,
        "flow_cta": flow_cta,
        "flow_token": flow_token,
        "screen": screen,
        "header": header,
        "footer": footer
    }
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GATEWAY_URL}/send/flow",
                json=payload,
                headers=headers,
                timeout=10.0
            )
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"Error enviando WhatsApp Flow: {e}")
        return False

# ─────────────────────────────────────────────
# FLUJOS PRINCIPALES
# ─────────────────────────────────────────────

async def send_welcome_menu(phone: str, internal_key: str, name: str = "", phone_number_id: Optional[str] = None):
    """Menú de bienvenida conciso y directo por opciones numeradas."""
    greeting = f"¡Hola{' ' + name if name else ''}! 👋"
    body = f"{greeting} Soy *Castor* 🦫\n¿En qué te podemos ayudar hoy?"
    buttons = [
        {"id": "flow_catalogo", "title": "🛍️ Catálogo y Precios"},
        {"id": "flow_asesor",   "title": "👨‍💼 Hablar con Asesor"},
        {"id": "flow_pedido",   "title": "📦 Consultar Pedido"},
        {"id": "flow_horarios", "title": "🕒 Horarios y Sucursales"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="🛠️ Ferretería Castor",
        footer="Responde 1, 2, 3 o 4",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_main_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Menú principal conciso para navegación continua."""
    body = "¿En qué más te podemos ayudar? 🦫"
    buttons = [
        {"id": "flow_catalogo", "title": "🛍️ Catálogo y Precios"},
        {"id": "flow_asesor",   "title": "👨‍💼 Hablar con Asesor"},
        {"id": "flow_pedido",   "title": "📦 Consultar Pedido"},
        {"id": "flow_horarios", "title": "🕒 Horarios y Sucursales"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="🛠️ Ferretería Castor",
        footer="Responde 1, 2, 3 o 4",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_catalog_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Alias para enviar el catálogo interactivo."""
    return await send_catalog_link(phone, internal_key, phone_number_id=phone_number_id)

async def send_catalog_link(phone: str, internal_key: str, phone_number_id: Optional[str] = None, sucursal: Optional[str] = "Centro"):
    """Envía el enlace al catálogo interactivo y opciones de categorías rápidas."""
    import os
    clean_phone = phone.replace("+", "").replace(" ", "").strip()
    ngrok_url = os.getenv("CATALOG_BASE_URL", "https://bot.autoeconomotors.com")
    catalog_url = f"{ngrok_url}/catalogo?phone={clean_phone}&sucursal={sucursal or 'Centro'}"
    
    body = (
        "🛍️ *Catálogo Ferretería Castor*\n\n"
        f"Abre la tienda online aquí:\n👉 {catalog_url}\n\n"
        "O explora una categoría rápida:"
    )
    buttons = [
        {"id": "cat_herramientas_elec", "title": "⚡ Eléctricas"},
        {"id": "cat_construccion",      "title": "🏗️ Construcción"},
        {"id": "flow_asesor",           "title": "👨‍💼 Asesor"},
        {"id": "menu_inicio",           "title": "🏠 Menú"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Responde 1, 2, 3 o 4",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_faq_list(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Lista de categorías de preguntas frecuentes."""
    sections = [
        {
            "title": "📋 Categorías",
            "rows": [
                {"id": "faq_envios",    "title": "🚚 Envíos y entregas",    "description": "Tiempos, costos y cobertura"},
                {"id": "faq_garantia",  "title": "🔧 Garantías",             "description": "Política de garantía y devolución"},
                {"id": "faq_horarios",  "title": "🕐 Horarios",             "description": "Horarios de la tienda"},
                {"id": "faq_pagos",     "title": "💳 Métodos de pago",       "description": "Formas de pago aceptadas"},
                {"id": "faq_ubicacion", "title": "📍 Ubicaciones",           "description": "Dónde encontrarnos"},
                {"id": "faq_mayoreo",   "title": "🏭 Compras al por mayor",   "description": "Descuentos por volumen"},
            ]
        }
    ]
    await _send_list(
        phone=phone,
        body="Selecciona la categoría sobre la que tienes dudas y te respondo al instante:",
        button_text="Ver categorías",
        sections=sections,
        header="❓ Preguntas Frecuentes",
        footer="Toca una opción para ver la respuesta",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_order_status_request(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Pide al usuario el número de pedido u operación."""
    await _send(
        phone=phone,
        message=(
            "📦 *Consulta de pedido*\n\n"
            "Por favor escribe el número de tu pedido u operación logística.\n\n"
            "_Ejemplo: OP-12345 o simplemente el número 12345_"
        ),
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_ticket_request(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Pide al usuario el número de ticket."""
    await _send(
        phone=phone,
        message=(
            "🎫 *Consulta de ticket*\n\n"
            "Por favor escribe el número de tu ticket de soporte.\n\n"
            "_Ejemplo: TKT-001 o simplemente el número 1_"
        ),
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def handle_order_result(phone: str, order_id: str, internal_key: str, redis_client: Any, phone_number_id: Optional[str] = None):
    """Consulta el estado del pedido usando la base de datos de órdenes del catálogo o logística."""
    clean_id = order_id.strip().upper().replace("#", "").strip()
    
    try:
        # 1. Intentar buscar en la base de datos de Órdenes del Catálogo
        from app.db.session import async_session
        from app.db.tables import Order, OrderItem
        from sqlalchemy import select

        db_order = None
        async with async_session() as session:
            stmt = select(Order).where(Order.order_number == clean_id)
            res = await session.execute(stmt)
            db_order = res.scalar_one_or_none()

            if db_order:
                stmt_items = select(OrderItem).where(OrderItem.order_id == db_order.id)
                res_items = await session.execute(stmt_items)
                order_items = res_items.scalars().all()

        if db_order is not None:
            STATUS_MAP = {
                "created": "⏳ Pedido recibido (En cola)",
                "picking": "📦 Preparando productos en bodega (Picking)",
                "dispatched": "🚚 Despachado / Listo para entrega",
                "in_route": "🛵 En camino a tu dirección",
                "delivered": "✅ Entregado con éxito",
                "cancelled": "❌ Cancelado"
            }
            status_text = STATUS_MAP.get(db_order.status, db_order.status)
            delivery_text = f"📍 Retiro en Sucursal *{db_order.sucursal or 'Centro'}*" if db_order.delivery_type == "pickup" else f"🚚 Envío a Domicilio: *{db_order.delivery_address}*"
            
            items_lines = [f"  • {it.quantity}x {it.product_name}" for it in order_items[:3]]
            if len(order_items) > 3:
                items_lines.append(f"  • ... y {len(order_items) - 3} producto(s) más")
            items_summary = "\n".join(items_lines) if items_lines else "  • Productos ferretería"

            msg = (
                f"📦 *Estado de tu Pedido #{db_order.order_number}*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Cliente:* {db_order.customer_name}\n"
                f"📊 *Estado:* {status_text}\n"
                f"{delivery_text}\n"
                f"💰 *Total:* ${float(db_order.total):.2f}\n\n"
                f"🛒 *Productos:*\n{items_summary}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"¿Necesitas consultar algo más?"
            )
        else:
            # 2. Consultar en Odoo ERP (sale.order)
            from app.services.odoo_service import OdooService
            odoo_service = OdooService()
            odoo_res = await odoo_service.get_order_status(clean_id)
            if odoo_res and odoo_res.get("found"):
                msg = (
                    f"📦 *Estado de tu Pedido Odoo ERP #{odoo_res['order_name']}*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 *Cliente:* {odoo_res['customer_name']}\n"
                    f"📊 *Estado:* {odoo_res['status_title']}\n"
                    f"🏢 *Almacén:* {odoo_res['warehouse']}\n"
                    f"📍 *Entrega:* {odoo_res['delivery_type']}\n"
                    f"💰 *Total:* ${odoo_res['total']:.2f}\n\n"
                    f"🛒 *Productos en Bodega:*\n  • {odoo_res['items_summary']}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"¿Necesitas consultar algo más?"
                )
            else:
                # 3. Fallback a operación logística legacy
                op_clean = clean_id.replace("OP-", "").replace("OP", "").strip()
                try:
                    op_id_int = int(op_clean)
                except ValueError:
                    op_id_int = None
                    
                op = None
                if op_id_int is not None:
                    auth_service = LogisticsAuthService(redis_client)
                    op_service = LogisticOperationService(auth_service)
                    op = await op_service.get_operation_by_id(op_id_int)
                
                if op is not None:
                    status_text = op.status_display or op.status
                    driver = op.raw_payload.get("driver_name", "Por asignar")
                    vehicle = op.raw_payload.get("vehicle", "Por asignar")
                    route = op.raw_payload.get("route", "N/A")
                    
                    msg = (
                        f"📦 *Pedido #{clean_id}*\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"Estado: {status_text}\n"
                        f"Ruta: {route}\n"
                        f"Conductor: {driver}\n"
                        f"Vehículo: {vehicle}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"¿Necesitas más ayuda?"
                    )
                else:
                    msg = (
                        f"🔍 No encontré el pedido *{order_id}*.\n\n"
                        "Verifica el número de orden (ej. *SO-2026-1048* o *CAST-2026-1042*) e inténtalo de nuevo, o contacta a un asesor si el problema persiste."
                    )
    except Exception as e:
        logger.error(f"Error fetching order {clean_id}: {str(e)}")
        msg = "⚠️ No pude consultar tu pedido en este momento. Intenta más tarde."

    # Enviar resultado + botones de acción
    buttons = [
        {"id": "flow_pedido",  "title": "🔄 Otro pedido"},
        {"id": "flow_asesor",  "title": "👨‍💼 Hablar con asesor"},
        {"id": "menu_inicio",  "title": "🏠 Menú principal"},
    ]
    await _send_buttons(
        phone=phone,
        body=msg,
        buttons=buttons,
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def handle_ticket_result(phone: str, ticket_id: str, internal_key: str, redis_client: Any, phone_number_id: Optional[str] = None):
    """Consulta el ticket usando el servicio interno y lo muestra con botones."""
    clean_id = ticket_id.strip().upper().replace("TKT-", "").replace("TKT", "").strip()
    
    try:
        try:
            ticket_id_int = int(clean_id)
        except ValueError:
            ticket_id_int = None
            
        ticket = None
        if ticket_id_int is not None:
            auth_service = LogisticsAuthService(redis_client)
            ticket_service = TicketService(auth_service)
            ticket = await ticket_service.get_ticket_by_id(ticket_id_int)
        
        if ticket is not None:
            status_text = ticket.status_display or ticket.status
            desc = ticket.description or "Sin descripción"
            order_num = ticket.raw_payload.get("order_number", "N/A")
            
            msg = (
                f"🎫 *Ticket #{clean_id}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Descripción: {desc}\n"
                f"Estado: {status_text}\n"
                f"Pedido Asociado: {order_num}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"¿Necesitas más ayuda?"
            )
        else:
            msg = (
                f"🔍 No encontré el ticket *{ticket_id}*.\n\n"
                "Verifica el número e inténtalo de nuevo."
            )
    except Exception as e:
        logger.error(f"Error fetching ticket {clean_id}: {str(e)}")
        msg = "⚠️ No pude consultar tu ticket en este momento."

    buttons = [
        {"id": "flow_ticket",  "title": "🔄 Otro ticket"},
        {"id": "flow_asesor",  "title": "👨‍💼 Hablar con asesor"},
        {"id": "menu_inicio",  "title": "🏠 Menú principal"},
    ]
    await _send_buttons(
        phone=phone,
        body=msg,
        buttons=buttons,
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_faq_answer(phone: str, faq_id: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Responde una pregunta frecuente específica."""
    answers = {
        "faq_envios": (
            "🚚 *Envíos y Entregas*\n\n"
            "• *Gratis* en compras superiores a *$150* dentro de Quito\n"
            "• *$5 adicionales* en compras menores a $150\n"
            "• Tiempo estándar: *24 a 48 horas hábiles*\n"
            "• Cobertura: Quito urbano y valles\n\n"
            "📞 Para entregas urgentes contáctanos directamente."
        ),
        "faq_garantia": (
            "🔧 *Garantía y Devoluciones*\n\n"
            "• *1 año* de garantía contra defectos de fabricación\n"
            "• Devoluciones: primeros *5 días hábiles* tras la compra\n"
            "• Requisitos: factura original + producto sin uso en empaque sellado\n\n"
            "⚠️ No aplica para desgaste normal de uso."
        ),
        "faq_horarios": (
            "🕐 *Horarios de Atención*\n\n"
            "• *Lunes a Viernes:* 07:30 AM – 06:00 PM\n"
            "• *Sábados:* 08:00 AM – 02:00 PM\n"
            "• *Domingos:* Cerrado 🚫\n\n"
            "Este chatbot está disponible *24/7* para consultas."
        ),
        "faq_pagos": (
            "💳 *Métodos de Pago*\n\n"
            "• Efectivo 💵\n"
            "• Tarjetas de crédito/débito 💳\n"
            "• Transferencia bancaria 🏦\n"
            "• PayPhone / Deuna 📱\n"
            "• Crédito directo (clientes registrados) 📋"
        ),
        "faq_ubicacion": (
            "📍 *Ubicaciones*\n\n"
            "🏪 *Sucursal Principal*\n"
            "Av. 10 de Agosto N45-23, Quito\n\n"
            "🏪 *Sucursal Norte*\n"
            "Av. Eloy Alfaro N56-10, Quito\n\n"
            "📌 Encuéntranos en Google Maps:\n"
            "https://maps.google.com/?q=Ferreteria+Castor+Quito"
        ),
        "faq_mayoreo": (
            "🏭 *Compras al Por Mayor*\n\n"
            "• Descuentos desde el *10%* en pedidos mayores a $500\n"
            "• Hasta *25%* para distribuidores registrados\n"
            "• Crédito disponible para empresas\n\n"
            "Para cotizaciones especiales, un asesor te atenderá personalmente."
        ),
    }
    
    answer = answers.get(faq_id, "❓ Lo siento, no tengo información sobre esa categoría en este momento.")
    
    # Enviar respuesta + botones de navegación
    buttons = [
        {"id": "flow_faq",    "title": "❓ Más preguntas"},
        {"id": "flow_asesor", "title": "👨‍💼 Hablar con asesor"},
        {"id": "menu_inicio", "title": "🏠 Menú principal"},
    ]
    await _send_buttons(
        phone=phone,
        body=answer,
        buttons=buttons,
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_advisor_confirmation(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Pregunta la sucursal de preferencia antes de transferir al asesor."""
    sections = [
        {
            "title": "🏪 Sucursales disponibles",
            "rows": [
                {"id": "confirm_asesor_norte", "title": "📍 Sucursal Norte", "description": "Av. Eloy Alfaro N56-10"},
                {"id": "confirm_asesor_centro", "title": "📍 Sucursal Centro", "description": "Av. 10 de Agosto (Principal)"},
                {"id": "confirm_asesor_sur", "title": "📍 Sucursal Sur", "description": "Sector Sur de Quito"},
                {"id": "confirm_asesor_cumbaya", "title": "📍 Sucursal Cumbayá", "description": "Vía Interoceánica Cumbayá"},
            ]
        }
    ]
    await _send_list(
        phone=phone,
        body=(
            "👨‍💼 *Atención por Sucursales*\n\n"
            "Te conectaremos con un asesor disponible.\n"
            "Por favor, selecciona de qué sucursal necesitas atención:"
        ),
        button_text="Seleccionar Sucursal",
        sections=sections,
        header="👨‍💼 Contactar Asesor",
        footer="Horario de asesores: L-V 7:30-18:00 / S 8:00-14:00",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_ai_response_with_menu(phone: str, ai_text: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra la respuesta de la IA y agrega botones de navegación."""
    # Truncar si es muy largo para WhatsApp
    if len(ai_text) > 900:
        ai_text = ai_text[:900] + "...\n\n_[respuesta truncada]_"
    
    buttons = [
        {"id": "flow_faq",    "title": "❓ Más preguntas"},
        {"id": "flow_asesor", "title": "👨‍💼 Hablar con asesor"},
        {"id": "menu_inicio", "title": "🏠 Menú principal"},
    ]
    await _send_buttons(
        phone=phone,
        body=ai_text,
        buttons=buttons,
        footer="Castor • Asistente Virtual",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )
