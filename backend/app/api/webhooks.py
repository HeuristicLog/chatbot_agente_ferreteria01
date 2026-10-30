"""
WhatsApp Webhook Router — Interactive Flow Engine
Handles both text messages and interactive button/list replies.
Routes to guided flows or LangChain AI for free-text questions.
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
from app.services.langchain_service import LangChainService
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
    clean_p = phone.replace("+", "").replace(" ", "").strip()
    norm_msg = (message or "").strip()
    
    # Marcar firmas en Redis para evitar bucles o ecos cruzados entre WhatsApp y Chatwoot
    import hashlib
    sig = hashlib.md5(f"{clean_p}:{norm_msg}".encode()).hexdigest()
    target_instance = "sucursal_centro"
    try:
        import redis.asyncio as aioredis
        import os
        r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        rc = aioredis.from_url(r_url)
        await rc.set(f"cw_to_evo:{sig}", "1", ex=60)
        await rc.set(f"wa_to_cw:{sig}", "1", ex=60)
        inst_bytes = await rc.get(f"user_instance:{clean_p}")
        if inst_bytes:
            target_instance = inst_bytes.decode('utf-8') if isinstance(inst_bytes, bytes) else str(inst_bytes)
        await rc.aclose()
    except Exception:
        pass

    # Sincronizar salida del bot con Chatwoot
    if sync_to_chatwoot:
        try:
            chatwoot = ChatwootService()
            if chatwoot.is_configured:
                await chatwoot.post_bot_message(phone, message, phone_number_id)
        except Exception as cw_err:
            logger.error(f"Error sincronizando salida de texto del bot con Chatwoot: {cw_err}")

    # 1. Si viene con credenciales explícitas de Meta Cloud (phone_number_id y access_token)
    if phone_number_id and access_token:
        headers = {"X-Internal-API-Key": internal_api_key}
        payload = {"phone": phone, "message": message, "phone_number_id": phone_number_id, "access_token": access_token}
        try:
            async with httpx.AsyncClient() as client:
                gw_resp = await client.post(f"{GATEWAY_URL}/send", json=payload, headers=headers, timeout=10.0)
                if gw_resp.status_code in [200, 201]:
                    return
        except Exception as gw_e:
            logger.debug(f"Gateway Meta Cloud send fallback: {gw_e}")

    # 2. Intentar enviar via Evolution API usando la instancia correspondiente (multilínea 25 números QR)
    try:
        async with httpx.AsyncClient() as client:
            evo_resp = await client.post(
                f"http://evolution-api:8080/message/sendText/{target_instance}",
                json={"number": clean_p, "text": message},
                headers={"apikey": "ferreteria_evolution_key_2026"},
                timeout=5.0
            )
            if evo_resp.status_code in [200, 201]:
                return
    except Exception as evo_e:
        logger.debug(f"Evolution send fallback: {evo_e}")

    # 3. Fallback general al Gateway
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

async def _gateway_send_media(phone: str, media_type: str, media_url: str, caption: str = "", phone_number_id: Optional[str] = None, access_token: Optional[str] = None):
    # 1. Si viene con credenciales explícitas de Meta Cloud (phone_number_id y access_token)
    if phone_number_id and access_token:
        headers = {"X-Internal-API-Key": internal_api_key}
        payload = {"phone": phone, "media_type": media_type, "media_url": media_url, "caption": caption, "phone_number_id": phone_number_id, "access_token": access_token}
        try:
            async with httpx.AsyncClient() as client:
                gw_resp = await client.post(f"{GATEWAY_URL}/send-media", json=payload, headers=headers, timeout=15.0)
                if gw_resp.status_code in [200, 201]:
                    return
        except Exception as gw_e:
            logger.debug(f"Gateway Meta Cloud send media fallback: {gw_e}")

    # 2. Intentar enviar via Evolution API (para WhatsApp QR vinculado multilínea)
    try:
        clean_p = phone.replace("+", "").replace(" ", "").strip()
        target_instance = "sucursal_centro"
        try:
            import redis.asyncio as aioredis
            import os
            r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            rc = aioredis.from_url(r_url)
            inst_bytes = await rc.get(f"user_instance:{clean_p}")
            if inst_bytes:
                target_instance = inst_bytes.decode('utf-8') if isinstance(inst_bytes, bytes) else str(inst_bytes)
            await rc.aclose()
        except Exception:
            pass

        evo_mediatype = media_type.lower()
        if "audio" in evo_mediatype or "voice" in evo_mediatype:
            evo_mediatype = "audio"
        elif "video" in evo_mediatype:
            evo_mediatype = "video"
        elif "image" in evo_mediatype or "photo" in evo_mediatype:
            evo_mediatype = "image"
        else:
            evo_mediatype = "document"

        async with httpx.AsyncClient() as client:
            if evo_mediatype == "audio":
                audio_resp = await client.post(
                    f"http://evolution-api:8080/message/sendWhatsAppAudio/{target_instance}",
                    json={"number": clean_p, "audio": media_url},
                    headers={"apikey": "ferreteria_evolution_key_2026"},
                    timeout=20.0
                )
                if audio_resp.status_code in [200, 201]:
                    return

            evo_payload = {
                "number": clean_p,
                "mediatype": evo_mediatype,
                "media": media_url,
                "caption": caption or ""
            }
            evo_resp = await client.post(
                "http://evolution-api:8080/message/sendMedia/sucursal_centro",
                json=evo_payload,
                headers={"apikey": "ferreteria_evolution_key_2026"},
                timeout=20.0
            )
            if evo_resp.status_code in [200, 201]:
                return
    except Exception as evo_e:
        logger.error(f"Evolution send media error: {evo_e}")

    headers = {"X-Internal-API-Key": internal_api_key}
    payload = {
        "phone": phone,
        "media_type": media_type,
        "media_url": media_url,
        "caption": caption
    }
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
    if access_token:
        payload["access_token"] = access_token
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{GATEWAY_URL}/send/media", json=payload, headers=headers, timeout=15.0)
    except Exception as e:
        logger.error(f"Gateway send_media error: {e}")

# ─── MAIN WEBHOOK ──────────────────────────────────────────────

@router.post("/webhooks/whatsapp", dependencies=[Depends(verify_internal_auth)])
async def receive_incoming_message(
    raw_payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis)
):
    session_service = SessionService(db, redis_client)
    ai_service = LangChainService()

    # Detectar formato: Evolution API v2 vs Gateway / Test Mock
    if "data" in raw_payload and isinstance(raw_payload["data"], dict) and "key" in raw_payload["data"]:
        data = raw_payload["data"]
        key = data.get("key", {})
            
        remote_jid = key.get("remoteJid", "")
        # Ignorar grupos de WhatsApp
        if "@g.us" in remote_jid:
            return {"status": "ignored_group"}
            
        # Resolver teléfono real (WhatsApp @lid vs número estándar)
        remote_jid_alt = key.get("remoteJidAlt", "") or data.get("remoteJidAlt", "")
        participant = key.get("participant", "") or data.get("participant", "")
        target_jid = remote_jid

        if "@lid" in target_jid:
            if remote_jid_alt and "@s.whatsapp.net" in remote_jid_alt:
                target_jid = remote_jid_alt
            elif participant and "@s.whatsapp.net" in participant:
                target_jid = participant
            else:
                lid_clean = target_jid.split("@")[0].split(":")[0]
                cached_p = await redis_client.get(f"lid_map:{lid_clean}")
                if cached_p:
                    target_jid = f"{cached_p.decode('utf-8') if isinstance(cached_p, bytes) else str(cached_p)}@s.whatsapp.net"
                else:
                    try:
                        import asyncpg
                        conn = await asyncpg.connect("postgresql://chatbot:change_me@postgres:5432/evolution")
                        row = await conn.fetchrow('SELECT "remoteJid" FROM "IsOnWhatsapp" WHERE "jidOptions" LIKE $1 LIMIT 1', f"%{lid_clean}%")
                        if not row:
                            row = await conn.fetchrow('SELECT "remoteJid" FROM "Contact" WHERE "remoteJid" LIKE $1 LIMIT 1', f"%{lid_clean}%")
                        await conn.close()
                        if row and row['remoteJid'] and "@s.whatsapp.net" in row['remoteJid']:
                            target_jid = row['remoteJid']
                            await redis_client.set(f"lid_map:{lid_clean}", target_jid.split("@")[0], ex=86400 * 7)
                    except Exception as db_e:
                        logger.debug(f"Error resolviendo lid en DB: {db_e}")

        phone = target_jid.split("@")[0].replace("+", "").replace(" ", "").strip()
        if not phone or phone in ["status", "0"]:
            return {"status": "ignored_no_phone"}

        # Guardar en caché mapeo lid -> teléfono real
        if "@lid" in remote_jid and phone:
            lid_c = remote_jid.split("@")[0].split(":")[0]
            await redis_client.set(f"lid_map:{lid_c}", phone, ex=86400 * 7)

        # Guardar instancia de procedencia para routing multilínea (25 números)
        curr_instance = raw_payload.get("instance") or "sucursal_centro"
        await redis_client.set(f"user_instance:{phone}", curr_instance, ex=86400 * 30)

        msg_obj = data.get("message", {}) or {}
        extracted_text = ""
        interactive_id = ""
        media_type = None
        media_mimetype = None
        media_filename = None
        
        if "conversation" in msg_obj and msg_obj["conversation"]:
            extracted_text = str(msg_obj["conversation"])
        elif "extendedTextMessage" in msg_obj and isinstance(msg_obj["extendedTextMessage"], dict):
            extracted_text = str(msg_obj["extendedTextMessage"].get("text", ""))
        elif "imageMessage" in msg_obj:
            media_type = "image"
            img_info = msg_obj["imageMessage"]
            extracted_text = img_info.get("caption") or "📷 [Foto / Imagen recibida]"
            media_mimetype = img_info.get("mimetype", "image/jpeg")
            media_filename = "imagen.jpg"
        elif "videoMessage" in msg_obj:
            media_type = "video"
            vid_info = msg_obj["videoMessage"]
            extracted_text = vid_info.get("caption") or "🎥 [Video recibido]"
            media_mimetype = vid_info.get("mimetype", "video/mp4")
            media_filename = "video.mp4"
        elif "audioMessage" in msg_obj:
            media_type = "audio"
            aud_info = msg_obj["audioMessage"]
            extracted_text = "🎙️ [Mensaje de voz / Audio recibido]"
            media_mimetype = aud_info.get("mimetype", "audio/ogg")
            media_filename = "audio.ogg"
        elif "documentMessage" in msg_obj:
            media_type = "document"
            doc_info = msg_obj["documentMessage"]
            media_filename = doc_info.get("fileName", "documento.pdf")
            extracted_text = doc_info.get("caption") or f"📄 [Documento recibido: {media_filename}]"
            media_mimetype = doc_info.get("mimetype", "application/pdf")
        elif "buttonsResponseMessage" in msg_obj:
            interactive_id = msg_obj["buttonsResponseMessage"].get("selectedButtonId", "")
            extracted_text = msg_obj["buttonsResponseMessage"].get("selectedDisplayText", interactive_id)
        elif "listResponseMessage" in msg_obj:
            single = msg_obj["listResponseMessage"].get("singleSelectReply", {})
            interactive_id = single.get("selectedRowId", "")
            extracted_text = msg_obj["listResponseMessage"].get("title", interactive_id)
        elif "templateButtonReplyMessage" in msg_obj:
            interactive_id = msg_obj["templateButtonReplyMessage"].get("selectedId", "")
            extracted_text = msg_obj["templateButtonReplyMessage"].get("selectedDisplayText", interactive_id)
            
        if not extracted_text and not interactive_id and not media_type:
            return {"status": "ignored_unsupported_type"}
            
        metadata = {
            "provider": "evolution",
            "push_name": data.get("pushName", ""),
            "instance": curr_instance
        }
        if media_type:
            metadata["media_type"] = media_type
            metadata["media_mimetype"] = media_mimetype
            metadata["media_filename"] = media_filename
            metadata["key"] = key
            metadata["raw_data"] = data
            media_b64 = data.get("base64") or msg_obj.get("base64")
            if not media_b64:
                for mkey in ["imageMessage", "audioMessage", "videoMessage", "documentMessage"]:
                    if mkey in msg_obj and isinstance(msg_obj[mkey], dict):
                        media_b64 = msg_obj[mkey].get("base64")
                        if media_b64:
                            break
            if media_b64:
                metadata["base64"] = media_b64
        if interactive_id:
            metadata["interactive_id"] = interactive_id

        # Deduplicación general de webhook por ID de mensaje de WhatsApp
        msg_id_val = key.get("id")
        if msg_id_val:
            is_new_webhook = await redis_client.set(f"evo_msg_seen:{msg_id_val}", "1", ex=300, nx=True)
            if not is_new_webhook:
                logger.info(f"Webhook duplicado ignorado de Evolution: {msg_id_val}")
                return {"status": "duplicate_webhook"}

        # Sincronización viceversa: Mensajes salientes desde WhatsApp Móvil o WhatsApp Web
        if key.get("fromMe", False):
            import hashlib
            norm_text = (extracted_text or "").strip()
            msg_sig = hashlib.md5(f"{phone}:{norm_text}".encode()).hexdigest()
            
            # Si fue originado por Chatwoot o el bot, ignorar eco
            if await redis_client.get(f"cw_to_evo:{msg_sig}") or (msg_id_val and await redis_client.get(f"cw_to_evo:{msg_id_val}")):
                logger.info(f"Mensaje saliente confirmado de WhatsApp (eco de Chatwoot): {msg_id_val}")
                return {"status": "ignored_echo_chatwoot"}

            logger.info(f"Mensaje saliente manual detectado desde WhatsApp ({phone}): {extracted_text[:50]}")
            # Registrar para que cuando Chatwoot emita su webhook no lo devuelva a WhatsApp
            await redis_client.set(f"wa_to_cw:{msg_sig}", "1", ex=60)
            if msg_id_val:
                await redis_client.set(f"wa_to_cw:{msg_id_val}", "1", ex=60)

            chatwoot = ChatwootService()
            if chatwoot.is_configured:
                try:
                    inbox_id = None
                    mapping = settings.whatsapp_inbox_mapping or {}
                    cw_contact_id = await chatwoot.get_or_create_contact(phone, f"Cliente +{phone}", inbox_id=inbox_id)
                    if cw_contact_id:
                        cw_conv_id = await chatwoot.get_or_create_conversation(cw_contact_id, inbox_id=inbox_id)
                        if cw_conv_id:
                            has_up = False
                            if media_type:
                                try:
                                    b64_raw = metadata.get("base64")
                                    if not b64_raw and key:
                                        async with httpx.AsyncClient() as client:
                                            b64_resp = await client.post(
                                                f"http://evolution-api:8080/chat/getBase64FromMediaMessage/{curr_instance}",
                                                json={"message": {"key": key}, "convertToMp4": False},
                                                headers={"apikey": "ferreteria_evolution_key_2026"},
                                                timeout=15.0
                                            )
                                            if b64_resp.status_code == 200:
                                                b64_raw = b64_resp.json().get("base64", "")
                                    if b64_raw:
                                        if "," in b64_raw:
                                            b64_raw = b64_raw.split(",", 1)[1]
                                        import base64
                                        f_bytes = base64.b64decode(b64_raw)
                                        f_name = metadata.get("media_filename") or f"adjunto_{msg_id_val}"
                                        f_mime = metadata.get("media_mimetype") or "application/octet-stream"
                                        has_up = await chatwoot.post_message_with_attachment(
                                            conversation_id=cw_conv_id,
                                            content=extracted_text if extracted_text not in ["📷 [Foto / Imagen recibida]", "🎥 [Video recibido]", "🎙️ [Mensaje de voz / Audio recibido]"] else "",
                                            file_bytes=f_bytes,
                                            filename=f_name,
                                            mimetype=f_mime,
                                            message_type="outgoing"
                                        )
                                except Exception as m_err:
                                    logger.error(f"Error procesando adjunto manual para Chatwoot: {m_err}")

                            if not has_up and extracted_text:
                                await chatwoot.post_message(cw_conv_id, extracted_text, message_type="outgoing")

                            # Registrar como conversación atendida por humano
                            try:
                                conv = await session_service.get_or_create_conversation(phone, provider="evolution")
                                conv.status = "human_active"
                                db.add(conv)
                                from app.db.tables import Message as DBMessage
                                db_msg = DBMessage(
                                    conversation_id=conv.id,
                                    direction="outbound",
                                    role="seller",
                                    content=extracted_text,
                                    message_type="text"
                                )
                                db.add(db_msg)
                                await db.commit()
                            except Exception as db_save_err:
                                logger.debug(f"Error guardando mensaje manual localmente: {db_save_err}")
                except Exception as cw_sync_err:
                    logger.error(f"Error sincronizando salida manual a Chatwoot: {cw_sync_err}")

            return {"status": "outbound_manual_synced_to_chatwoot"}
            
        payload = IncomingWhatsAppMessage(
            phone=phone,
            message=extracted_text,
            message_id=key.get("id"),
            metadata=metadata
        )
    else:
        # Formato Gateway estándar / Simulator / Pytest
        if not raw_payload.get("phone") or not raw_payload.get("message"):
            return {"status": "ignored_invalid_payload"}
        payload = IncomingWhatsAppMessage(**raw_payload)

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
    if payload.message_id:
        msg_id_key = f"msg_id:{payload.message_id}"
        if await redis_client.get(msg_id_key):
            return {"status": "duplicate"}
        await redis_client.set(msg_id_key, "1", ex=3600)

    sanitized = sanitize_user_input(payload.message)

    # ── Registrar métricas de mensajes entrantes y tiempo de espera para FRT ──
    try:
        import time
        await redis_client.incr("metrics:inbound_messages")
        clean_p = payload.phone.replace("+", "").replace(" ", "").strip()
        await redis_client.set(f"cust_wait_ts:{clean_p}", int(time.time()), nx=True, ex=86400)

        in_mtype = payload.metadata.get("media_type")
        if in_mtype == "image":
            await redis_client.incr("metrics:images")
        elif in_mtype == "audio":
            await redis_client.incr("metrics:audios")
        elif in_mtype == "video":
            await redis_client.incr("metrics:videos")
        elif in_mtype == "document":
            await redis_client.incr("metrics:documents")
    except Exception as met_err:
        logger.debug(f"Error registrando métricas entrantes: {met_err}")

    # ── Sincronizar mensaje entrante con Chatwoot (desde el inicio) ──
    chatwoot = ChatwootService()
    cw_conv_id = None
    if chatwoot.is_configured:
        try:
            inbox_id = None
            mapping = settings.whatsapp_inbox_mapping or {}
            if dest_phone_number_id and dest_phone_number_id in mapping:
                inbox_id = mapping[dest_phone_number_id].get("inbox_id")
            
            cw_contact_id = await chatwoot.get_or_create_contact(payload.phone, f"Cliente +{payload.phone}", inbox_id=inbox_id)
            if cw_contact_id:
                cw_conv_id = await chatwoot.get_or_create_conversation(cw_contact_id, inbox_id=inbox_id)
                if cw_conv_id:
                    media_type = payload.metadata.get("media_type")
                    msg_key = payload.metadata.get("key")
                    has_uploaded_media = False
                    if media_type:
                        try:
                            b64_raw = payload.metadata.get("base64")
                            if not b64_raw and msg_key:
                                # Descargar archivo multimedia desde Evolution API pasando exactamente key
                                async with httpx.AsyncClient() as client:
                                    inst = payload.metadata.get("instance", "sucursal_centro")
                                    b64_resp = await client.post(
                                        f"http://evolution-api:8080/chat/getBase64FromMediaMessage/{inst}",
                                        json={"message": {"key": msg_key}, "convertToMp4": False},
                                        headers={"apikey": "ferreteria_evolution_key_2026"},
                                        timeout=15.0
                                    )
                                    if b64_resp.status_code == 200:
                                        b64_raw = b64_resp.json().get("base64", "")
                            
                            if b64_raw:
                                if "," in b64_raw:
                                    b64_raw = b64_raw.split(",", 1)[1]
                                import base64
                                f_bytes = base64.b64decode(b64_raw)
                                f_name = payload.metadata.get("media_filename") or f"adjunto_{payload.message_id}"
                                f_mime = payload.metadata.get("media_mimetype") or "application/octet-stream"
                                has_uploaded_media = await chatwoot.post_message_with_attachment(
                                    conversation_id=cw_conv_id,
                                    content=sanitized if sanitized not in ["📷 [Foto / Imagen recibida]", "🎥 [Video recibido]", "🎙️ [Mensaje de voz / Audio recibido]"] else "",
                                    file_bytes=f_bytes,
                                    filename=f_name,
                                    mimetype=f_mime,
                                    message_type="incoming"
                                )
                        except Exception as m_err:
                            logger.error(f"Error procesando adjunto para Chatwoot: {m_err}")

                    if not has_uploaded_media:
                        await chatwoot.post_message(cw_conv_id, sanitized, message_type="incoming")

                    # Mantener abierta y visible la conversación en Chatwoot
                    await chatwoot.update_conversation_status(cw_conv_id, "open")

                    # Actualizar atributos personalizados y etiquetas en tiempo real en Chatwoot
                    try:
                        cust_attrs = {}
                        labels = []
                        if media_type:
                            cust_attrs["adjuntos_recibidos"] = f"Archivo {media_type.capitalize()}"
                            labels.append(f"adjunto-{media_type}")

                        clean_lower = sanitized.lower()
                        if any(k in clean_lower for k in ["camioneta", "pickup", "4x4", "dmax", "d-max", "hilux", "poer"]):
                            cust_attrs["flujo_actual"] = "Camionetas 4x4"
                            labels.append("camionetas-4x4")
                            if "d-max" in clean_lower or "dmax" in clean_lower:
                                cust_attrs["modelo_interes"] = "Chevrolet D-Max 3.0L"
                            elif "hilux" in clean_lower:
                                cust_attrs["modelo_interes"] = "Toyota Hilux 2.4L"
                            elif "poer" in clean_lower:
                                cust_attrs["modelo_interes"] = "Great Wall Poer 2.0L"
                        elif any(k in clean_lower for k in ["hibrido", "híbrido", "yaris", "pico y placa"]):
                            cust_attrs["flujo_actual"] = "Híbridos Cero Pico y Placa"
                            cust_attrs["modelo_interes"] = "Toyota Yaris Cross Híbrido"
                            labels.append("hibrido-0-pico-y-placa")
                        elif any(k in clean_lower for k in ["suv", "suvs", "sportage", "tracker", "tucson", "sonet", "tiggo"]):
                            cust_attrs["flujo_actual"] = "SUVs Familiares"
                            labels.append("suv-familiar")
                        elif any(k in clean_lower for k in ["credito", "crédito", "cuota", "financiamiento", "entrada"]):
                            cust_attrs["flujo_actual"] = "Simulación Crédito"
                            labels.append("credito-vehicular")
                        elif any(k in clean_lower for k in ["retoma", "usado", "mi auto"]):
                            cust_attrs["flujo_actual"] = "Plan Retoma"
                            labels.append("plan-retoma")
                        elif any(k in clean_lower for k in ["test drive", "testdrive", "prueba"]):
                            cust_attrs["flujo_actual"] = "Test Drive"
                            labels.append("test-drive")

                        if cust_attrs:
                            await chatwoot.set_conversation_custom_attributes(cw_conv_id, cust_attrs)
                        if labels:
                            await chatwoot.add_conversation_labels(cw_conv_id, labels)
                    except Exception as meta_cw_err:
                        logger.debug(f"Error actualizando custom_attributes en Chatwoot: {meta_cw_err}")
        except Exception as cw_err:
            logger.error(f"Error sincronizando mensaje entrante con Chatwoot: {cw_err}")

    # ── Modo Chatbot AutoEcuador Motors Activo ──
    BOT_ENABLED = True
    if not BOT_ENABLED:
        await save_message(db, conv.id, "inbound", "user", sanitized, payload.message_id)
        logger.info(f"Modo Chatwoot activo (Bot pausado). Mensaje recibido de {payload.phone}: {sanitized}")
        return {"status": "chatwoot_direct_mode"}

    # ── 1. Active Handoff Lock ─────────────────────────────────
    clean_check = sanitized.lower().strip()
    reset_keywords = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "menú", "inicio", "start", "bot", "reiniciar"]
    if any(clean_check.startswith(kw) or clean_check == kw for kw in reset_keywords):
        conv.status = "bot_active"
        await db.commit()
    elif conv.status in ["waiting_agent", "assigned", "human_active", "handed_over"]:
        await save_message(db, conv.id, "inbound", "user", sanitized, payload.message_id)
        event = {"type": "new_message", "data": {"conversation_id": str(conv.id), "direction": "inbound", "role": "user", "content": sanitized}}
        await redis_client.publish("seller_updates", json.dumps(event))

        if conv.status == "waiting_agent":
            reply = "Tu solicitud sigue en espera. ✋ Pronto un asesor te atenderá. Gracias por tu paciencia."
            target_access_token = None
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
            await flows.send_welcome_menu(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Menú principal automotriz enviado")
            return {"status": "processed"}

        # ── Flujo Automotriz: Menú de Vehículos / Categorías
        if interactive_id == "auto_menu_vehiculos":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_vehicle_types_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Categorías de vehículos enviadas")
            return {"status": "processed"}

        # ── Flujo Automotriz: Horarios y Sedes
        if interactive_id == "auto_horarios":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_horarios_info(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Horarios y sedes enviados")
            return {"status": "processed"}

        # ── Flujo Automotriz: Categoría Camionetas 4x4
        if interactive_id == "auto_cat_pickups":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_pickups_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Flujo de camionetas 4x4 enviado")
            return {"status": "processed"}

        # ── Flujo Automotriz: Categoría SUVs
        if interactive_id == "auto_cat_suvs":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_suvs_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Flujo de SUVs enviado")
            return {"status": "processed"}

        # ── Flujo Automotriz: Categoría Híbridos / Eléctricos
        if interactive_id == "auto_cat_hibridos":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_hibridos_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Flujo de híbridos enviado")
            return {"status": "processed"}

        # ── Flujo Automotriz: Simulación de Crédito por rangos
        if interactive_id == "auto_flow_credito":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_credito_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Flujo de crédito vehicular enviado")
            return {"status": "processed"}

        if interactive_id in ["auto_down_3to5", "auto_down_5to8", "auto_down_more8"]:
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_credito_range_result(payload.phone, interactive_id, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", f"Resultado de financiamiento para {interactive_id} enviado")
            return {"status": "processed"}

        # ── Flujo Automotriz: Plan Retoma (Auto Usado)
        if interactive_id == "auto_flow_retoma" or interactive_id == "auto_tasar_usado":
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_retoma_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Flujo de plan retoma enviado")
            return {"status": "processed"}

        # ── Flujo Automotriz: Agendar Test Drive
        if interactive_id in ["auto_flow_testdrive", "auto_td_pickups", "auto_td_suvs", "auto_td_hibridos"]:
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_testdrive_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Flujo de test drive enviado")
            return {"status": "processed"}

        if interactive_id in ["auto_td_domicilio", "auto_td_showroom"]:
            await clear_flow_state(redis_client, payload.phone)
            await flows.confirm_testdrive_preference(payload.phone, interactive_id, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", f"Confirmación de test drive {interactive_id} enviada")
            return {"status": "processed"}

        # ── Flujo: Catálogo Oficial (Pantalla emergente Webview)
        if interactive_id in ["flow_catalogo", "auto_view_vitrina"]:
            await clear_flow_state(redis_client, payload.phone)
            await flows.send_catalog_link(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
            await save_message(db, conv.id, "outbound", "assistant", "Catálogo interactivo enviado")
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

        # ── Respuesta de Meta WhatsApp Flow (Pantalla nativa completada)
        if interactive_id == "flow_response":
            await clear_flow_state(redis_client, payload.phone)
            flow_data = payload.metadata.get("flow_response_data", {})
            from app.services import in_chat_cart_service as in_chat_cart
            cart = await in_chat_cart.get_cart(redis_client, payload.phone)
            cart["customer_name"] = flow_data.get("nombre") or "Cliente WhatsApp"
            cart["delivery_type"] = flow_data.get("tipo_entrega") or "pickup"
            cart["sucursal"] = flow_data.get("sucursal") or "Centro"
            cart["address"] = flow_data.get("direccion")
            await in_chat_cart.save_cart(redis_client, payload.phone, cart)
            
            # Cargar productos del flow al carrito
            prods = flow_data.get("productos", [])
            if isinstance(prods, str):
                prods = [prods]
            for p_sku in prods:
                await in_chat_cart.add_item_to_cart(redis_client, payload.phone, p_sku, 1)
                
            payment_method = flow_data.get("metodo_pago", "efectivo")
            await in_chat_cart.complete_in_chat_order(
                payload.phone, redis_client, db, payment_method, internal_api_key, phone_number_id=dest_phone_number_id
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
            await _do_handoff(payload.phone, conv, db, redis_client, ai_service, session_id, sucursal=suc_name, phone_number_id=dest_phone_number_id)
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

    # Mensajes multimedia entrantes (Fotos, Videos, Audios, Documentos)
    if payload.metadata.get("media_type"):
        mtype = payload.metadata.get("media_type")
        m_msg = "¡Muchas gracias! 📁 Hemos recibido tu archivo adjunto. Un asesor comercial humano lo revisará en Chatwoot para atenderte."
        if mtype == "audio":
            m_msg = "¡Muchas gracias! 🎙️ Hemos recibido tu nota de voz. Nuestro equipo comercial la escuchará de inmediato en Chatwoot para atenderte."
        elif mtype == "image":
            m_msg = "¡Muchas gracias! 📷 Hemos recibido tu imagen. Nuestro equipo comercial la revisará de inmediato en Chatwoot para asesorarte."
        elif mtype == "video":
            m_msg = "¡Muchas gracias! 🎥 Hemos recibido tu video. Nuestro equipo comercial lo revisará de inmediato en Chatwoot para atenderte."

        buttons = [
            {"id": "auto_menu_vehiculos", "title": "🚘 Ver Vehículos"},
            {"id": "auto_flow_credito", "title": "💳 Simular Crédito"},
            {"id": "flow_asesor", "title": "👨‍💼 Hablar con Asesor"}
        ]
        await flows._send_buttons(payload.phone, m_msg, buttons, header="AutoEcuador Motors", internal_key=internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", m_msg)
        return {"status": "processed"}

    # Saludos y Menú Principal
    greeting_words = ["hola", "hi", "hello", "buenas", "buenos", "hey", "buen dia", "buenos dias", "inicio", "start", "menu", "menú", "0", "volver al menu"]
    if any(clean_msg.startswith(g) or clean_msg == g for g in greeting_words):
        await clear_flow_state(redis_client, payload.phone)
        await flows.send_welcome_menu(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Menú de bienvenida enviado")
        return {"status": "processed"}

    # 1. Ver Vehículos / Modelos / Categorías (Opción 1 del menú)
    if clean_msg in ["1", "1.", "ver vehiculos", "ver vehículos", "vehiculos", "vehículos", "modelos", "catalogo", "catálogo", "autos", "carros"]:
        await clear_flow_state(redis_client, payload.phone)
        await flows.send_vehicle_types_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Categorías de vehículos enviadas")
        return {"status": "processed"}

    # 2. Horarios y Sedes / Showrooms (Opción 2 del menú)
    horarios_keywords = ["2", "2.", "horario", "horarios", "a que hora", "a qué hora", "hora", "abren", "cierran", "atencion", "atención", "donde estan", "dónde están", "ubicacion", "ubicación", "showroom", "showrooms", "sede", "sedes", "direccion", "dirección", "donde queda", "dónde queda"]
    if any(k in clean_msg for k in horarios_keywords) or clean_msg in ["2", "2.", "horarios"]:
        await clear_flow_state(redis_client, payload.phone)
        await flows.send_horarios_info(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Información de horarios y sedes enviada")
        return {"status": "processed"}

    # 3. Hablar con Asesor Humano / Transferencia (Opción 3 del menú)
    advisor_keywords = ["3", "3.", "asesor", "asesora", "hablar con asesor", "hablar con un asesor", "comunicarme con un asesor", "humano", "agente", "atencion al cliente", "atención al cliente", "persona", "ejecutivo", "ejecutiva", "vendedor"]
    if any(k in clean_msg for k in advisor_keywords) or clean_msg in ["3", "3.", "asesor"]:
        await flows.send_advisor_confirmation(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Opciones de asesor por sucursal enviadas")
        return {"status": "processed"}

    # Simular Crédito / Cuotas
    credito_keywords = ["credito", "crédito", "simular credito", "simular crédito", "financiamiento", "cuotas", "cuota", "prestamo", "préstamo"]
    if any(k in clean_msg for k in credito_keywords):
        await clear_flow_state(redis_client, payload.phone)
        await flows.send_credito_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Flujo de crédito vehicular enviado")
        return {"status": "processed"}

    # Plan Retoma / Auto Usado
    retoma_keywords = ["retoma", "plan retoma", "usado", "auto usado", "carro usado", "tasar usado", "parte de pago", "avaluo", "avalúo"]
    if any(k in clean_msg for k in retoma_keywords):
        await clear_flow_state(redis_client, payload.phone)
        await flows.send_retoma_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Flujo de plan retoma enviado")
        return {"status": "processed"}

    # Test Drive / Prueba de Manejo
    testdrive_keywords = ["test drive", "testdrive", "prueba de manejo", "probar auto", "probar carro", "manejar"]
    if any(k in clean_msg for k in testdrive_keywords):
        await clear_flow_state(redis_client, payload.phone)
        await flows.send_testdrive_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Flujo de test drive enviado")
        return {"status": "processed"}

    # Catálogo / Productos / Tienda Meta WhatsApp Flow (Pantalla emergente nativa)
    catalog_keywords = ["catalogo", "catálogo", "productos", "inventario", "precios", "tienda", "comprar", "lista de productos"]
    if any(k in clean_msg for k in catalog_keywords):
        await clear_flow_state(redis_client, payload.phone)
        sent = await flows.send_catalog_flow(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        if not sent:
            from app.services import in_chat_cart_service as in_chat_cart
            await in_chat_cart.send_categories_menu(payload.phone, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Catálogo interactivo enviado")
        return {"status": "processed"}

    # Ver Carrito directo
    if "carrito" in clean_msg or "mi carrito" in clean_msg:
        await clear_flow_state(redis_client, payload.phone)
        from app.services import in_chat_cart_service as in_chat_cart
        await in_chat_cart.send_cart_view(payload.phone, redis_client, internal_api_key, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", "Vista de carrito enviada")
        return {"status": "processed"}

    # Código de Pedido directo (ej. CAST-2026-1024 o OP-101)
    if clean_msg.startswith("cast-") or clean_msg.startswith("op-") or clean_msg.startswith("#cast-") or clean_msg.startswith("#op-"):
        await clear_flow_state(redis_client, payload.phone)
        await flows.handle_order_result(payload.phone, sanitized, internal_api_key, redis_client, phone_number_id=dest_phone_number_id)
        await save_message(db, conv.id, "outbound", "assistant", f"Consulta de pedido {sanitized}")
        return {"status": "processed"}

    # ── 4.5 Asistente Comercial Automotriz Inteligente (AutoEcuador Motors) ──
    from app.services.auto_sales_assistant import process_auto_sales_message
    handled = await process_auto_sales_message(payload.phone, sanitized, db, redis_client, internal_api_key, phone_number_id=dest_phone_number_id)
    if handled:
        await save_message(db, conv.id, "outbound", "assistant", "Respuesta comercial automotriz enviada")
        return {"status": "processed", "session_id": session_id}

    # ── 5. Free-text → LangChain Automotive AI ─────────────────────────────
    ai_response = await ai_service.get_prediction(sanitized, session_id, phone=payload.phone)
    await save_message(db, conv.id, "outbound", "assistant", ai_response)

    # Enviar respuesta IA con botones de navegación
    await flows.send_ai_response_with_menu(payload.phone, ai_response, internal_api_key, phone_number_id=dest_phone_number_id)
    return {"status": "processed", "session_id": session_id}


async def _do_handoff(phone: str, conv, db, redis_client, ai_service: Optional[LangChainService] = None, session_id: str = "", sucursal: Optional[str] = None, phone_number_id: Optional[str] = None):
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
            try:
                await redis_client.incr("metrics:handoffs")
            except Exception:
                pass
            return  # HandoffService already sent the appropriate welcome/queue message to the client
            
        msg = "⚠️ No pudimos conectarte en este momento. Por favor intenta más tarde o llámanos directamente."
        
        target_access_token = None
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
            await redis_client.set(f"cw_out_sent:{msg_id}", "1", ex=120)

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

        if phone:
            clean_phone = phone.replace("+", "").strip()
            norm_content = (content or "").strip()
            import hashlib
            cw_sig = hashlib.md5(f"{clean_phone}:{norm_content}".encode()).hexdigest()

            # Evitar rebotes: Si este mensaje fue escrito en WhatsApp (móvil/web), NO volver a enviarlo a WhatsApp
            if await redis_client.get(f"wa_to_cw:{cw_sig}") or (msg_id and await redis_client.get(f"wa_to_cw:{msg_id}")):
                logger.info(f"Ignorando reenvío a WhatsApp: mensaje originado en WhatsApp ({msg_id})")
                return {"status": "ignored_origin_whatsapp"}

            # Registrar que este mensaje va de Chatwoot a WhatsApp para que Evolution no lo duplique
            await redis_client.set(f"cw_to_evo:{cw_sig}", "1", ex=60)
            if msg_id:
                await redis_client.set(f"cw_to_evo:{msg_id}", "1", ex=60)

            # ── Medir tiempo de respuesta (FRT) del asesor y métricas de salida ──
            try:
                wait_ts = await redis_client.get(f"cust_wait_ts:{clean_phone}")
                frt_delta = None
                if wait_ts:
                    import time
                    frt_delta = int(time.time()) - int(wait_ts)
                    if 0 <= frt_delta < 86400:
                        await redis_client.lpush("metrics:frt_samples", str(frt_delta))
                        await redis_client.ltrim("metrics:frt_samples", 0, 100)
                    await redis_client.delete(f"cust_wait_ts:{clean_phone}")
                await redis_client.incr("metrics:outbound_messages")

                # Actualizar métrica de FRT y etiqueta en Chatwoot
                cw_conv_id = conversation.get("id")
                if cw_conv_id and frt_delta is not None:
                    frt_display = f"{frt_delta}s" if frt_delta < 60 else f"{frt_delta // 60}m {frt_delta % 60}s"
                    chatwoot_service = ChatwootService()
                    await chatwoot_service.set_conversation_custom_attributes(cw_conv_id, {
                        "tiempo_respuesta_frt": frt_display,
                        "flujo_actual": "Atendido por Asesor Humano"
                    })
                    label = "frt-rapido" if frt_delta <= 60 else "frt-normal"
                    await chatwoot_service.add_conversation_labels(cw_conv_id, [label, "atendido-asesor"])
            except Exception as frt_err:
                logger.debug(f"Error registrando FRT en chatwoot_webhook: {frt_err}")

            # Cuando un asesor humano responde en Chatwoot, pasamos el estado a human_active para que el bot pause sus respuestas automáticas
            try:
                from app.services.session_service import SessionService
                session_id = SessionService.derive_session_id(clean_phone, target_phone_number_id)
                from app.repositories.conversation_repository import ConversationRepository
                repo = ConversationRepository(db)
                conv = await repo.get_by_session_id(session_id)
                if conv:
                    conv.status = "human_active"
                    db.add(conv)
                    await db.commit()
            except Exception as check_err:
                logger.error(f"Error actualizando estado a human_active: {check_err}")

            # 1. Reenvío de adjuntos multimedia (fotos, videos, audios, documentos)
            attachments = payload.get("attachments", [])
            has_sent_media = False
            if attachments:
                for att in attachments:
                    file_url = att.get("data_url") or att.get("file_url")
                    file_type = att.get("file_type", "image")
                    if file_url:
                        logger.info(f"Reenvío de adjunto Chatwoot ({file_type}) a WhatsApp ({clean_phone}): {file_url}")
                        await _gateway_send_media(
                            clean_phone,
                            media_type=file_type,
                            media_url=file_url,
                            caption=content or "",
                            phone_number_id=target_phone_number_id,
                            access_token=target_access_token
                        )
                        has_sent_media = True

            # 2. Reenvío de texto si no fue enviado como caption de adjunto
            if content and not has_sent_media:
                logger.info(f"Reenvío de Chatwoot a WhatsApp ({clean_phone}, inbox: {inbox_id}, phone_number_id: {target_phone_number_id}): {content[:50]}...")
                try:
                    await _gateway_send_text(clean_phone, content, phone_number_id=target_phone_number_id, access_token=target_access_token, sync_to_chatwoot=False)

                    # Registrar mensaje localmente
                    from app.db.tables import Message as DBMessage
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

                        msg = "✅ *Atención al cliente finalizada.* El asesor comercial virtual Alex de AutoEcuador Motors 🇪🇨 vuelve a estar activo. Escribe *hola* para ver el menú o explorar vehículos."
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
