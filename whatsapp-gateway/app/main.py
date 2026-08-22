import os
import logging
import httpx
import json
import datetime
from fastapi import FastAPI, Request, Response, HTTPException, status, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import redis

from app.models import OutgoingMessage, IncomingMessage
from app.providers.base import WhatsAppProvider
from app.providers.mock import MockWhatsAppProvider
from app.providers.meta import MetaWhatsAppProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("whatsapp-gateway")

app = FastAPI(title="WhatsApp Gateway", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

provider_type = os.getenv("WHATSAPP_PROVIDER", "mock").lower()
verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
chatbot_api_url = os.getenv("CHATBOT_API_URL", "http://backend:8080")
internal_api_key = os.getenv("INTERNAL_API_KEY", "change_me")
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

try:
    r_client = redis.from_url(redis_url, decode_responses=True)
except Exception as e:
    logger.warning(f"Could not connect to Redis: {str(e)}")
    r_client = None

provider: WhatsAppProvider

if provider_type == "meta":
    logger.info("Initializing Meta WhatsApp Provider")
    provider = MetaWhatsAppProvider(
        verify_token=verify_token,
        access_token=access_token,
        phone_number_id=phone_number_id
    )
else:
    logger.info("Initializing Mock WhatsApp Provider")
    provider = MockWhatsAppProvider()

def verify_internal_auth(x_internal_api_key: Optional[str] = Header(None, alias="X-Internal-API-Key")):
    if not x_internal_api_key or x_internal_api_key != internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Llave de API interna incorrecta.")

# ─── Request Models ────────────────────────────────────────────

class ButtonsPayload(BaseModel):
    phone: str
    body: str
    buttons: List[Dict[str, str]]     # [{"id": "...", "title": "..."}]
    header: Optional[str] = ""
    footer: Optional[str] = ""
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None

class ListPayload(BaseModel):
    phone: str
    body: str
    button_text: str
    sections: List[Dict]              # WhatsApp sections format
    header: Optional[str] = ""
    footer: Optional[str] = ""
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None

# ─── Health ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "provider": provider_type}

# ─── Webhook Verification ──────────────────────────────────────

@app.get("/webhooks/whatsapp")
async def verify_meta_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode and token:
        if mode == "subscribe" and token == verify_token:
            logger.info("Meta Webhook verificado.")
            return Response(content=challenge, media_type="text/plain")
        raise HTTPException(status_code=403, detail="Verification token mismatch")
    return {"status": "running"}

# ─── Incoming Webhook ──────────────────────────────────────────

@app.post("/webhooks/whatsapp")
async def incoming_whatsapp_payload(request: Request):
    try:
        raw_payload = await request.json()
    except Exception:
        raw_payload = {}
    logger.debug(f"Webhook payload: {raw_payload}")
    
    messages = await provider.parse_incoming_message(raw_payload)
    headers = {"X-Internal-API-Key": internal_api_key, "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        for msg in messages:
            try:
                logger.info(f"Forwarding message from {msg.phone} to Backend")
                await client.post(
                    f"{chatbot_api_url}/webhooks/whatsapp",
                    json=msg.model_dump(),
                    headers=headers,
                    timeout=15.0
                )
            except Exception as e:
                logger.error(f"Error forwarding message: {str(e)}")
    return {"status": "received", "count": len(messages)}


# ─── Chatwoot Webhook Proxy ────────────────────────────────────

@app.post("/webhooks/chatwoot")
async def proxy_chatwoot_webhook(request: Request):
    try:
        raw_payload = await request.json()
    except Exception:
        raw_payload = {}
    
    logger.info("Forwarding Chatwoot webhook payload to Backend")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{chatbot_api_url}/webhooks/chatwoot",
                json=raw_payload,
                timeout=15.0
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))
        except Exception as e:
            logger.error(f"Error forwarding Chatwoot webhook: {str(e)}")
            raise HTTPException(status_code=502, detail="Error forwarding Chatwoot webhook to Backend.")


# ─── Send Text ─────────────────────────────────────────────────

@app.post("/send", dependencies=[Depends(verify_internal_auth)])
async def send_outgoing_message(payload: OutgoingMessage):
    if payload.interactive_options:
        success = await provider.send_interactive_options(
            to_phone=payload.phone,
            message=payload.message,
            options=payload.interactive_options,
            phone_number_id=payload.phone_number_id,
            access_token=payload.access_token
        )
    else:
        success = await provider.send_text_message(
            to_phone=payload.phone,
            message=payload.message,
            phone_number_id=payload.phone_number_id,
            access_token=payload.access_token
        )
    _log_outbound(payload.phone, payload.message)
    if success:
        return {"status": "sent"}
    raise HTTPException(status_code=502, detail="No fue posible enviar el mensaje.")

# ─── Send Interactive Buttons ──────────────────────────────────

@app.post("/send/buttons", dependencies=[Depends(verify_internal_auth)])
async def send_buttons(payload: ButtonsPayload):
    if not hasattr(provider, "send_interactive_buttons"):
        # Fallback: send as plain text with options listed
        text = payload.body + "\n\n" + "\n".join([f"• {b['title']}" for b in payload.buttons])
        success = await provider.send_text_message(
            payload.phone,
            text,
            phone_number_id=payload.phone_number_id,
            access_token=payload.access_token
        )
    else:
        success = await provider.send_interactive_buttons(
            to_phone=payload.phone,
            body=payload.body,
            buttons=payload.buttons,
            header=payload.header or "",
            footer=payload.footer or "",
            phone_number_id=payload.phone_number_id,
            access_token=payload.access_token
        )
    _log_outbound(payload.phone, payload.body)
    if success:
        return {"status": "sent"}
    raise HTTPException(status_code=502, detail="No fue posible enviar los botones.")

# ─── Send List Message ─────────────────────────────────────────

@app.post("/send/list", dependencies=[Depends(verify_internal_auth)])
async def send_list(payload: ListPayload):
    if not hasattr(provider, "send_list_message"):
        # Fallback: plain text
        text = payload.body + "\n\n"
        for sec in payload.sections:
            for row in sec.get("rows", []):
                text += f"• {row['title']}\n"
        success = await provider.send_text_message(
            payload.phone,
            text,
            phone_number_id=payload.phone_number_id,
            access_token=payload.access_token
        )
    else:
        success = await provider.send_list_message(
            to_phone=payload.phone,
            body=payload.body,
            button_text=payload.button_text,
            sections=payload.sections,
            header=payload.header or "",
            footer=payload.footer or "",
            phone_number_id=payload.phone_number_id,
            access_token=payload.access_token
        )
    _log_outbound(payload.phone, payload.body)
    if success:
        return {"status": "sent"}
    raise HTTPException(status_code=502, detail="No fue posible enviar la lista.")

# ─── Outbound Logs ─────────────────────────────────────────────

def _log_outbound(phone: str, message: str):
    if r_client:
        try:
            log_payload = {"phone": phone, "message": message, "direction": "outbound", "timestamp": datetime.datetime.now().isoformat()}
            r_client.lpush("whatsapp_outbound_logs", json.dumps(log_payload))
            r_client.ltrim("whatsapp_outbound_logs", 0, 49)
        except Exception:
            pass

@app.get("/outbound")
async def get_outbound_logs(phone: Optional[str] = None):
    if not r_client:
        return {"success": False, "data": []}
    try:
        raw_logs = r_client.lrange("whatsapp_outbound_logs", 0, -1)
        logs = [json.loads(log) for log in raw_logs]
        if phone:
            logs = [log for log in logs if log.get("phone") == phone]
        return {"success": True, "data": logs}
    except Exception as e:
        return {"success": False, "error": str(e)}
