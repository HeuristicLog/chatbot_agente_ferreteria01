import logging
import httpx
from typing import List, Dict, Any, Optional
from app.providers.base import WhatsAppProvider
from app.models import IncomingMessage

logger = logging.getLogger("whatsapp-gateway.meta-provider")

class MetaWhatsAppProvider(WhatsAppProvider):
    def __init__(self, verify_token: str, access_token: str, phone_number_id: str):
        self.verify_token = verify_token
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"

    async def parse_incoming_message(self, raw_payload: Dict[str, Any]) -> List[IncomingMessage]:
        logger.debug(f"Parsing Meta webhook payload: {raw_payload}")
        messages: List[IncomingMessage] = []
        
        entry = raw_payload.get("entry", [])
        if not entry:
            return messages
            
        for e in entry:
            changes = e.get("changes", [])
            for c in changes:
                value = c.get("value", {})
                metadata_info = value.get("metadata", {})
                dest_phone_number_id = metadata_info.get("phone_number_id")
                msgs = value.get("messages", [])
                
                for msg in msgs:
                    phone = msg.get("from")
                    msg_id = msg.get("id")
                    msg_type = msg.get("type")
                    text_content = ""
                    media_url = None
                    media_type = None
                    interactive_id = None   # button_id or list_id clicked
                    
                    if msg_type == "text":
                        text_content = msg.get("text", {}).get("body", "")
                    elif msg_type == "button":
                        text_content = msg.get("button", {}).get("text", "")
                        interactive_id = msg.get("button", {}).get("payload", "")
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        int_type = interactive.get("type")
                        if int_type == "button_reply":
                            br = interactive.get("button_reply", {})
                            text_content = br.get("title", "")
                            interactive_id = br.get("id", "")
                        elif int_type == "list_reply":
                            lr = interactive.get("list_reply", {})
                            text_content = lr.get("title", "")
                            interactive_id = lr.get("id", "")
                        elif int_type == "nfm_reply":
                            # WhatsApp Flow response
                            nfm = interactive.get("nfm_reply", {})
                            text_content = nfm.get("name", "flow_response")
                            interactive_id = "flow_response"
                    elif msg_type in ["image", "document", "video", "audio"]:
                        media_data = msg.get(msg_type, {})
                        media_id = media_data.get("id")
                        media_url = f"https://graph.facebook.com/v20.0/{media_id}"
                        media_type = media_data.get("mime_type")
                        text_content = media_data.get("caption", f"[{msg_type.upper()}]")
                        
                    if phone and msg_id:
                        # Build metadata with interactive_id for flow routing
                        metadata = {"raw_message": msg}
                        if dest_phone_number_id:
                            metadata["phone_number_id"] = dest_phone_number_id
                        if interactive_id:
                            metadata["interactive_id"] = interactive_id
                            metadata["is_interactive"] = True
                            
                        messages.append(
                            IncomingMessage(
                                phone=phone,
                                message=text_content,
                                message_id=msg_id,
                                media_url=media_url,
                                media_type=media_type,
                                metadata=metadata
                            )
                        )
                        
        return messages

    async def send_text_message(self, to_phone: str, message: str, **kwargs) -> bool:
        phone_number_id = kwargs.get("phone_number_id") or self.phone_number_id
        access_token = kwargs.get("access_token") or self.access_token
        api_url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json=payload, headers=headers, timeout=10.0)
                if response.status_code in [200, 201]:
                    logger.info(f"Meta text message sent to {to_phone} via phone_number_id {phone_number_id}")
                    return True
                logger.error(f"Failed to send Meta message: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Meta message: {str(e)}")
            return False

    async def send_interactive_buttons(self, to_phone: str, body: str, buttons: List[Dict], header: str = "", footer: str = "", **kwargs) -> bool:
        """Send up to 3 quick reply buttons."""
        phone_number_id = kwargs.get("phone_number_id") or self.phone_number_id
        access_token = kwargs.get("access_token") or self.access_token
        api_url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
        headers_http = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        btn_list = []
        for btn in buttons[:3]:
            btn_list.append({
                "type": "reply",
                "reply": {
                    "id": btn.get("id", f"btn_{len(btn_list)}"),
                    "title": btn.get("title", "")[:20]
                }
            })
        
        interactive_payload: Dict[str, Any] = {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": btn_list}
        }
        if header:
            interactive_payload["header"] = {"type": "text", "text": header}
        if footer:
            interactive_payload["footer"] = {"text": footer}
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": interactive_payload
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json=payload, headers=headers_http, timeout=10.0)
                if response.status_code in [200, 201]:
                    logger.info(f"Interactive buttons sent to {to_phone} via phone_number_id {phone_number_id}")
                    return True
                logger.error(f"Failed to send buttons: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending buttons: {str(e)}")
            return False

    async def send_list_message(self, to_phone: str, body: str, button_text: str, sections: List[Dict], header: str = "", footer: str = "", **kwargs) -> bool:
        """Send a list message with up to 10 items."""
        phone_number_id = kwargs.get("phone_number_id") or self.phone_number_id
        access_token = kwargs.get("access_token") or self.access_token
        api_url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
        headers_http = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        sanitized_sections = []
        for sec in sections[:10]:
            sec_title = (sec.get("title") or "Opciones")[:24]
            sec_rows = []
            for row in sec.get("rows", [])[:10]:
                sec_rows.append({
                    "id": str(row.get("id", ""))[:200],
                    "title": str(row.get("title", ""))[:24],
                    "description": str(row.get("description", ""))[:72]
                })
            sanitized_sections.append({
                "title": sec_title,
                "rows": sec_rows
            })

        interactive_payload: Dict[str, Any] = {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": str(button_text)[:20],
                "sections": sanitized_sections
            }
        }
        if header:
            interactive_payload["header"] = {"type": "text", "text": str(header)[:60]}
        if footer:
            interactive_payload["footer"] = {"text": str(footer)[:60]}
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": interactive_payload
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json=payload, headers=headers_http, timeout=10.0)
                if response.status_code in [200, 201]:
                    logger.info(f"List message sent to {to_phone} via phone_number_id {phone_number_id}")
                    return True
                logger.error(f"Failed to send list: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending list: {str(e)}")
            return False

    async def send_interactive_options(self, to_phone: str, message: str, options: List[str], **kwargs) -> bool:
        """Legacy: send up to 3 buttons from a list of strings."""
        buttons = [{"id": f"opt_{i}", "title": opt} for i, opt in enumerate(options[:3])]
        return await self.send_interactive_buttons(to_phone, message, buttons, **kwargs)

    async def mark_as_read(self, message_id: str) -> bool:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=10.0)
                return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
            return False

    async def download_media(self, media_id: str) -> Optional[bytes]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with httpx.AsyncClient() as client:
                media_meta_url = f"https://graph.facebook.com/v20.0/{media_id}"
                response = await client.get(media_meta_url, headers=headers, timeout=10.0)
                if response.status_code != 200:
                    return None
                download_url = response.json().get("url")
                media_response = await client.get(download_url, headers=headers, timeout=30.0)
                if media_response.status_code == 200:
                    return media_response.content
                return None
        except Exception as e:
            logger.error(f"Error downloading Meta media: {str(e)}")
            return None
