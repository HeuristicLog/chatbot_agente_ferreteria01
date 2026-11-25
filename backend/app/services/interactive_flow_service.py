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
# HELPERS — Enviar mensajes al Gateway / Evolution / Meta Cloud
# ─────────────────────────────────────────────

async def _send_meta_text(phone: str, message: str, phone_number_id: Optional[str] = None, access_token: Optional[str] = None) -> bool:
    """Envía mensaje de texto directamente por Meta WhatsApp Cloud API."""
    from app.config import settings
    token = access_token or settings.WHATSAPP_ACCESS_TOKEN
    pid = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID or "1508804275641424"
    if not token or not pid:
        return False
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    url = f"https://graph.facebook.com/v22.0/{pid}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_p,
        "type": "text",
        "text": {"body": message}
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in [200, 201]:
                logger.info(f"Texto Meta Cloud API enviado a {clean_p}: {r.status_code}")
                return True
            else:
                logger.warning(f"Error Meta texto {clean_p}: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Excepción enviando texto a Meta: {e}")
    return False

async def _send_meta_cta_url(phone: str, body: str, display_text: str, url: str, header_image_url: Optional[str] = None, header_text: Optional[str] = None, footer: str = "Ferretería Castor • Compras en WhatsApp", phone_number_id: Optional[str] = None, access_token: Optional[str] = None) -> bool:
    """Envía un botón nativo de tipo CTA URL (que abre el In-App Browser dentro de WhatsApp en 1 solo flujo)."""
    from app.config import settings
    token = access_token or settings.WHATSAPP_ACCESS_TOKEN
    pid = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID or "1508804275641424"
    if not token or not pid:
        return False
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    api_url = f"https://graph.facebook.com/v22.0/{pid}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Meta limita display_text a máximo 20 caracteres
    short_text = (display_text or "Abrir Tienda 🛍️")[:20]
    
    interactive_data = {
        "type": "cta_url",
        "body": {"text": body[:1024]},
        "footer": {"text": footer[:60]},
        "action": {
            "name": "cta_url",
            "parameters": {
                "display_text": short_text,
                "url": url
            }
        }
    }
    if header_image_url:
        interactive_data["header"] = {
            "type": "image",
            "image": {"link": header_image_url}
        }
    elif header_text:
        interactive_data["header"] = {
            "type": "text",
            "text": header_text[:60]
        }
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_p,
        "type": "interactive",
        "interactive": interactive_data
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(api_url, json=payload, headers=headers)
            if r.status_code in [200, 201]:
                logger.info(f"CTA URL Meta enviado a {clean_p}: {r.status_code}")
                return True
            else:
                logger.warning(f"Error Meta CTA URL {clean_p}: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Excepción enviando CTA URL a Meta: {e}")
    return False

async def _send_meta_image(phone: str, image_url: str, caption: Optional[str] = None, phone_number_id: Optional[str] = None, access_token: Optional[str] = None) -> bool:
    """Envía imagen con caption directamente por Meta WhatsApp Cloud API."""
    from app.config import settings
    token = access_token or settings.WHATSAPP_ACCESS_TOKEN
    pid = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID or "1508804275641424"
    if not token or not pid or not image_url:
        return False
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    url = f"https://graph.facebook.com/v22.0/{pid}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    img_data = {"link": image_url}
    if caption:
        img_data["caption"] = caption[:1024]
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_p,
        "type": "image",
        "image": img_data
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in [200, 201]:
                logger.info(f"Imagen Meta enviada exitosamente a {clean_p}: {r.status_code}")
                return True
            else:
                logger.warning(f"Error enviando imagen Meta {clean_p}: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Excepción enviando imagen Meta: {e}")
    return False

async def _send_image(phone: str, image_url: str, caption: str = "", phone_number_id: Optional[str] = None, instance: Optional[str] = None) -> bool:
    """Despacha una imagen a WhatsApp con fallbacks robustos (Meta Cloud API -> Evolution API)."""
    if not image_url:
        return False
    # 1. Meta WhatsApp Cloud API
    if await _send_meta_image(phone, image_url, caption=caption, phone_number_id=phone_number_id):
        await _save_db_message(phone, f"[Imagen: {image_url}] {caption}", msg_type="image")
        return True

    # 2. Evolution API
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    target_inst = instance or ("bonilla_1085" if "992451085" in clean_p else "sucursal_centro")
    headers = {"apikey": "ferreteria_evolution_key_2026"}
    for base in EVOLUTION_CANDIDATE_URLS:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.post(
                    f"{base}/message/sendMedia/{target_inst}",
                    json={
                        "number": clean_p,
                        "media": image_url,
                        "mediatype": "image",
                        "caption": caption
                    },
                    headers=headers
                )
                if resp.status_code in [200, 201]:
                    await _save_db_message(phone, f"[Imagen: {image_url}] {caption}", msg_type="image")
                    return True
        except Exception:
            continue
    return False

async def _send_meta_buttons(phone: str, body: str, buttons: list, header: str = "", footer: str = "", header_image_url: Optional[str] = None, phone_number_id: Optional[str] = None, access_token: Optional[str] = None) -> bool:
    """Envía botones o lista interactiva nativa directamente por Meta WhatsApp Cloud API con soporte de cabecera de imagen."""
    from app.config import settings
    token = access_token or settings.WHATSAPP_ACCESS_TOKEN
    pid = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID or "1508804275641424"
    if not token or not pid:
        return False
    
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    url = f"https://graph.facebook.com/v22.0/{pid}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    if 1 <= len(buttons) <= 3:
        btn_objs = []
        for idx, b in enumerate(buttons):
            bid = b.get("id", f"btn_{idx}")
            btitle = b.get("title", "")[:20]
            btn_objs.append({"type": "reply", "reply": {"id": bid, "title": btitle}})
        
        interactive_data = {
            "type": "button",
            "body": {"text": body[:1024]},
            "action": {"buttons": btn_objs}
        }
        if header_image_url:
            interactive_data["header"] = {
                "type": "image",
                "image": {"link": header_image_url}
            }
        elif header:
            interactive_data["header"] = {"type": "text", "text": header[:60]}
        if footer:
            interactive_data["footer"] = {"text": footer[:60]}
    else:
        rows = []
        for idx, b in enumerate(buttons):
            rid = b.get("id", f"row_{idx}")
            rtitle = b.get("title", "")[:24]
            rdesc = b.get("description", "Seleccionar opción")[:72]
            rows.append({"id": rid, "title": rtitle, "description": rdesc})
        
        interactive_data = {
            "type": "list",
            "body": {"text": body[:1024]},
            "action": {
                "button": "Ver Opciones",
                "sections": [{"title": "Opciones Disponibles", "rows": rows}]
            }
        }
        if header:
            interactive_data["header"] = {"type": "text", "text": header[:60]}
        if footer:
            interactive_data["footer"] = {"text": footer[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_p,
        "type": "interactive",
        "interactive": interactive_data
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in [200, 201]:
                logger.info(f"Botones interactivos Meta enviados a {clean_p}: {r.status_code}")
                return True
            else:
                logger.warning(f"Error Meta interactivo {clean_p}: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Excepción enviando interactivo a Meta: {e}")
    return False

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

    # 1. Si está activo Meta Cloud API (token presente), enviar directo por Graph API
    if await _send_meta_text(phone, message, phone_number_id=phone_number_id):
        return

    # 2. Intentar despacho por Evolution API (WhatsApp Baileys QR)
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

async def _send_evolution_buttons(phone: str, body: str, buttons: list, header: str = "", footer: str = "", instance: Optional[str] = None, phone_number_id: Optional[str] = None) -> bool:
    """Intenta enviar botones o lista interactiva nativa a través de Evolution API v2."""
    global _working_evo_url
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    target_inst = instance
    if not target_inst and phone_number_id:
        if str(phone_number_id) in ["593992451085", "151924"]:
            target_inst = "bonilla_1085"
        elif str(phone_number_id) in ["593988921136", "150556"]:
            target_inst = "sucursal_centro"

    if not target_inst:
        target_inst = "bonilla_1085" if "992451085" in clean_p else "sucursal_centro"

    headers = {"apikey": "ferreteria_evolution_key_2026"}
    candidates = list(EVOLUTION_CANDIDATE_URLS)
    if _working_evo_url and _working_evo_url in candidates:
        candidates.remove(_working_evo_url)
        candidates.insert(0, _working_evo_url)

    # Si son hasta 3 botones, usar sendButtons. Si son 4 o más, usar sendList
    for base in candidates:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                if len(buttons) <= 3:
                    btn_payload = {
                        "number": clean_p,
                        "title": header or "🛠️ Ferretería Castor",
                        "description": body,
                        "footer": footer or "Selecciona una opción",
                        "buttons": [
                            {
                                "buttonId": b.get("id", f"btn_{idx}"),
                                "buttonText": {"displayText": b.get("title", "")[:20]},
                                "type": 1
                            } for idx, b in enumerate(buttons)
                        ]
                    }
                    resp = await client.post(f"{base}/message/sendButtons/{target_inst}", json=btn_payload, headers=headers)
                else:
                    list_payload = {
                        "number": clean_p,
                        "title": header or "🛠️ Ferretería Castor",
                        "description": body,
                        "buttonText": "📋 Ver Opciones",
                        "footerText": footer or "Selecciona una opción",
                        "sections": [
                            {
                                "title": "Menú Disponible",
                                "rows": [
                                    {
                                        "rowId": b.get("id", f"row_{idx}"),
                                        "title": b.get("title", "")[:24],
                                        "description": b.get("description", "Toca para abrir")[:70]
                                    } for idx, b in enumerate(buttons)
                                ]
                            }
                        ]
                    }
                    resp = await client.post(f"{base}/message/sendList/{target_inst}", json=list_payload, headers=headers)

                if resp.status_code in [200, 201]:
                    _working_evo_url = base
                    logger.info(f"Botones interactivos despachados via Evolution API ({base}/{target_inst}) a {clean_p}")
                    return True
        except Exception:
            continue
    return False

async def _send_buttons(phone: str, body: str, buttons: list, header: str = "", footer: str = "", header_image_url: Optional[str] = None, internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje 100% interactivo por flujos y botones (sin pedir números ni opciones manuales)."""
    clean_p = phone.replace("+", "").replace(" ", "").strip()

    # Guardar en Redis mapeo inteligente para que cualquier toque o palabra active el flujo
    try:
        import redis.asyncio as aioredis
        import os
        r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        rc = aioredis.from_url(r_url)
        for idx, b in enumerate(buttons):
            act_id = b.get("id", str(idx+1))
            await rc.set(f"btn_opt:{clean_p}:{idx+1}", act_id, ex=900)
            clean_title = (b.get("title", "")).lower().strip()
            # Mapear título completo y palabras clave (ej: 'catálogo', 'carrito', 'asesor', 'pagar')
            await rc.set(f"btn_title:{clean_p}:{clean_title}", act_id, ex=900)
            for word in clean_title.split():
                if len(word) > 3 and word not in ["para", "menu", "menú", "hola"]:
                    await rc.set(f"btn_title:{clean_p}:{word}", act_id, ex=900)
        await rc.aclose()
    except Exception:
        pass

    # 1. Si está activo Meta Cloud API (token presente), enviar botones o lista nativa por Graph API
    if await _send_meta_buttons(phone, body, buttons, header=header, footer=footer, header_image_url=header_image_url, phone_number_id=phone_number_id):
        await _save_db_message(phone, f"[{header}] {body}")
        return

    # 2. Intentar despacho como botones/lista nativa de WhatsApp en Evolution API
    if await _send_evolution_buttons(phone, body, buttons, header=header, footer=footer, phone_number_id=phone_number_id):
        # Guardar en base de datos
        await _save_db_message(phone, f"[{header}] {body}")
        return

    # 2. Formato interactivo visual limpio (sin números ni instrucciones de escribir dígitos)
    btn_lines = []
    for b in buttons:
        btn_lines.append(f"▶️ *{b.get('title')}*")

    parts = []
    if header:
        parts.append(f"*{header}*")
    parts.append(body)
    if btn_lines:
        parts.append("\n".join(btn_lines))
    
    prompt_footer = footer or "Toca una opción para continuar"
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

    # Despacho por Evolution API (Texto interactivo con opciones)
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

async def _send_meta_list(phone: str, body: str, button_text: str, sections: list, header: str = "", footer: str = "", phone_number_id: Optional[str] = None, access_token: Optional[str] = None) -> bool:
    """Envía un menú interactivo tipo LIST nativo de Meta WhatsApp Cloud API."""
    from app.config import settings
    token = access_token or settings.WHATSAPP_ACCESS_TOKEN
    pid = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID or "1508804275641424"
    if not token or not pid:
        return False
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    url = f"https://graph.facebook.com/v22.0/{pid}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    meta_sections = []
    for sec in sections:
        rows = []
        for r in sec.get("rows", []):
            rid = str(r.get("id", ""))[:200]
            rtitle = str(r.get("title", ""))[:24]
            rdesc = str(r.get("description", ""))[:72] if r.get("description") else None
            row_dict = {"id": rid, "title": rtitle}
            if rdesc:
                row_dict["description"] = rdesc
            rows.append(row_dict)
        if rows:
            meta_sections.append({
                "title": str(sec.get("title", "Opciones"))[:24],
                "rows": rows
            })
            
    interactive_data = {
        "type": "list",
        "body": {"text": body[:1024]},
        "action": {
            "button": (button_text or "Ver Opciones")[:20],
            "sections": meta_sections
        }
    }
    if header:
        interactive_data["header"] = {"type": "text", "text": header[:60]}
    if footer:
        interactive_data["footer"] = {"text": footer[:60]}
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_p,
        "type": "interactive",
        "interactive": interactive_data
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in [200, 201]:
                logger.info(f"Lista interactiva Meta enviada exitosamente a {clean_p}: {r.status_code}")
                return True
            else:
                logger.warning(f"Error enviando lista interactiva Meta a {clean_p}: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Excepción enviando lista interactiva Meta: {e}")
    return False

async def _send_list(phone: str, body: str, button_text: str, sections: list, header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje con lista de opciones 100% interactiva sin números ni URLs externas."""
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    
    # 1. Si está activo Meta Cloud API, despachar lista interactiva nativa por Graph API
    if await _send_meta_list(phone, body, button_text, sections, header=header, footer=footer, phone_number_id=phone_number_id):
        await _save_db_message(phone, f"[{header}] {body}")
        return

    sec_lines = []
    opt_idx = 1
    
    # Guardar en Redis mapeo temporal inteligente
    try:
        import redis.asyncio as aioredis
        import os
        r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        rc = aioredis.from_url(r_url)
        for sec in sections:
            for row in sec.get('rows', []):
                row_id = row.get('id', str(opt_idx))
                await rc.set(f"btn_opt:{clean_p}:{opt_idx}", row_id, ex=900)
                clean_t = row.get('title', '').lower().strip()
                await rc.set(f"btn_title:{clean_p}:{clean_t}", row_id, ex=900)
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
# FLUJOS PRINCIPALES INTERACTIVOS (100% BOTONES Y NAVEGACIÓN)
# ─────────────────────────────────────────────

async def _record_prev_menu(phone: str, menu_id: str):
    """Guarda en Redis el último menú visitado para permitir botón '⬅️ Anterior'."""
    try:
        import redis.asyncio as aioredis
        import os
        clean_p = phone.replace("+", "").replace(" ", "").strip()
        r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        rc = aioredis.from_url(r_url)
        await rc.set(f"prev_menu:{clean_p}", menu_id, ex=1800)
        await rc.aclose()
    except Exception:
        pass

async def send_welcome_menu(phone: str, internal_key: str, name: str = "", phone_number_id: Optional[str] = None):
    """Menú de bienvenida 100% por flujos y botones interactivos (sin solicitar números)."""
    await _record_prev_menu(phone, "menu_inicio")
    greeting = f"¡Hola{' ' + name if name else ''}! 👋"
    body = (
        f"{greeting} Soy *Castor* 🦫, tu asistente virtual de *Ferretería Castor*.\n\n"
        "¿En qué te podemos ayudar hoy? Selecciona una opción:"
    )
    buttons = [
        {"id": "flow_catalogo", "title": "🛍️ Catálogo"},
        {"id": "cart_view",     "title": "🛒 Mi Carrito"},
        {"id": "flow_faq",      "title": "❓ Preguntas Frecuentes"},
        {"id": "flow_asesor",   "title": "👨‍💼 Hablar con Asesor"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="🛠️ Ferretería Castor",
        footer="Toca una opción para continuar",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_main_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Menú principal interactivo con navegación continua."""
    return await send_welcome_menu(phone, internal_key, phone_number_id=phone_number_id)

async def send_faq_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Menú interactivo de preguntas frecuentes con navegación atrás e inicio."""
    await _record_prev_menu(phone, "menu_inicio")
    body = (
        "❓ *Preguntas Frecuentes* 🦫\n\n"
        "Selecciona el tema sobre el que deseas consultar información:"
    )
    buttons = [
        {"id": "faq_horarios", "title": "🕒 Horarios y Sucursales"},
        {"id": "faq_envios",   "title": "🚚 Envíos y Despachos"},
        {"id": "faq_pagos",    "title": "💳 Formas de Pago"},
        {"id": "nav_inicio",   "title": "🏠 Inicio"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="❓ Centro de Ayuda",
        footer="Toca una opción para ver la respuesta",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_catalog_in_app(phone: str, internal_key: str = "change_me", phone_number_id: Optional[str] = None, sucursal: Optional[str] = "Centro"):
    """Envía la tarjeta interactiva de apertura de la Tienda Castor In-App (Opción A: 1 solo flujo sin spam de mensajes)."""
    import os
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    ngrok_url = os.getenv("CATALOG_BASE_URL", "https://usable-thorn-kabob.ngrok-free.dev")
    catalog_url = f"{ngrok_url}/catalogo?phone={clean_p}&sucursal={sucursal}&ngrok-skip-browser-warning=1"
    
    header_img = "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=800&auto=format&fit=crop&q=80"
    body = (
        "🛠️ *TIENDA DIGITAL FERRETERÍA CASTOR* 🦫\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Explora nuestro catálogo e-commerce interactivo en *una sola pantalla* sin saturar tu chat de mensajes:\n\n"
        "✨ *Todo en un solo lugar:*\n"
        "• 🔍 *Buscador en tiempo real:* Escribe y filtra al instante.\n"
        "• 🏷️ *Marcas y Departamentos:* DeWalt, Makita, Stanley, Truper, Selvalegre.\n"
        "• 🔩 *Tornillería completa:* Más de 10 variedades de fijaciones.\n"
        "• 🛒 *Carrito en vivo:* Suma, resta (+ / −) y calcula tu IVA sin mensajes repetitivos.\n\n"
        "Toca el botón abajo para abrir la tienda 👇"
    )
    
    # 1. Intentar enviar botón nativo CTA URL por Meta Cloud API
    sent = await _send_meta_cta_url(
        phone=clean_p,
        body=body,
        display_text="Abrir Tienda 🛍️",
        url=catalog_url,
        header_image_url=header_img,
        phone_number_id=phone_number_id
    )
    if sent:
        await _save_db_message(clean_p, body)
        return
        
    # 2. Fallback si no está Meta Cloud API (Texto limpio con link directo)
    fallback_msg = f"{body}\n\n👉 *Toca aquí para abrir:* {catalog_url}"
    await _send(clean_p, fallback_msg, internal_key, phone_number_id=phone_number_id)

async def send_catalog_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra el catálogo interactivo In-App."""
    return await send_catalog_in_app(phone, internal_key, phone_number_id=phone_number_id)

async def send_catalog_link(phone: str, internal_key: str, phone_number_id: Optional[str] = None, sucursal: Optional[str] = "Centro"):
    """Muestra el catálogo interactivo In-App."""
    return await send_catalog_in_app(phone, internal_key, phone_number_id=phone_number_id, sucursal=sucursal)

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
        {"id": "flow_catalogo",      "title": "🛍️ Ver Catálogo"},
        {"id": "flow_search_prompt", "title": "🔍 Buscar Producto"},
        {"id": "cart_view",          "title": "🛒 Ver Mi Carrito"},
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
        {"id": "flow_catalogo",      "title": "🛍️ Ver Catálogo"},
        {"id": "flow_search_prompt", "title": "🔍 Buscar Producto"},
        {"id": "cart_view",          "title": "🛒 Ver Mi Carrito"},
    ]
    await _send_buttons(
        phone=phone,
        body=ai_text,
        buttons=buttons,
        footer="Castor • Asistente Virtual",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )
