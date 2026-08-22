import logging
from typing import List, Dict, Any, Optional
from app.providers.base import WhatsAppProvider
from app.models import IncomingMessage

logger = logging.getLogger("whatsapp-gateway.mock-provider")

class MockWhatsAppProvider(WhatsAppProvider):
    async def parse_incoming_message(self, raw_payload: Dict[str, Any]) -> List[IncomingMessage]:
        logger.info(f"Mock parsing incoming payload: {raw_payload}")
        phone = raw_payload.get("phone", "593999999999")
        message = raw_payload.get("message", "")
        message_id = raw_payload.get("message_id", "mock-msg-123")
        media_url = raw_payload.get("media_url")
        media_type = raw_payload.get("media_type")
        return [
            IncomingMessage(
                phone=phone,
                message=message,
                message_id=message_id,
                media_url=media_url,
                media_type=media_type,
                metadata=raw_payload.get("metadata", {})
            )
        ]

    async def send_text_message(self, to_phone: str, message: str, **kwargs) -> bool:
        logger.info(f"[MOCK → {to_phone}] TEXT: {message[:80]}")
        return True

    async def send_interactive_options(self, to_phone: str, message: str, options: List[str], **kwargs) -> bool:
        opts = " | ".join([f"[{o}]" for o in options])
        logger.info(f"[MOCK → {to_phone}] BUTTONS: {message[:60]} | {opts}")
        return True

    async def send_interactive_buttons(self, to_phone: str, body: str, buttons: List[Dict], header: str = "", footer: str = "", **kwargs) -> bool:
        btns = " | ".join([f"[{b.get('title','')}]" for b in buttons])
        logger.info(f"[MOCK → {to_phone}] INTERACTIVE: {body[:60]} | {btns}")
        return True

    async def send_list_message(self, to_phone: str, body: str, button_text: str, sections: List[Dict], header: str = "", footer: str = "", **kwargs) -> bool:
        rows = []
        for sec in sections:
            for row in sec.get("rows", []):
                rows.append(row.get("title", ""))
        logger.info(f"[MOCK → {to_phone}] LIST: {body[:60]} | {', '.join(rows)}")
        return True

    async def mark_as_read(self, message_id: str) -> bool:
        logger.info(f"[MOCK READ]: {message_id}")
        return True

    async def download_media(self, media_id: str) -> Optional[bytes]:
        return b"mock-media-bytes"
