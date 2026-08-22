import logging
import httpx
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger("chatbot-api.services.chatwoot")

class ChatwootService:
    def __init__(self):
        self.base_url = settings.CHATWOOT_BASE_URL.rstrip("/")
        self.api_token = settings.CHATWOOT_API_TOKEN
        self.account_id = settings.CHATWOOT_ACCOUNT_ID
        self.inbox_id = settings.CHATWOOT_INBOX_ID

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_or_create_contact(self, phone: str, name: str, inbox_id: Optional[int] = None) -> Optional[int]:
        """Busca un contacto por teléfono en Chatwoot, o lo crea si no existe."""
        if not self.is_configured:
            logger.warning("Chatwoot no está configurado (falta CHATWOOT_API_TOKEN).")
            return None

        # Formatear teléfono para Chatwoot (debe empezar con +)
        formatted_phone = phone if phone.startswith("+") else f"+{phone}"

        # 1. Buscar contacto
        headers = self._get_headers()
        try:
            async with httpx.AsyncClient() as client:
                search_url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/search?q={formatted_phone}"
                resp = await client.get(search_url, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    payload = resp.json()
                    contacts = payload.get("payload", [])
                    if contacts:
                        contact_id = contacts[0].get("id")
                        logger.info(f"Contacto encontrado en Chatwoot: ID {contact_id}")
                        return contact_id

            # 2. Crear contacto si no existe
            target_inbox_id = inbox_id or self.inbox_id
            create_payload = {
                "name": name or f"Cliente {phone}",
                "phone_number": formatted_phone,
                "inbox_id": target_inbox_id
            }
            async with httpx.AsyncClient() as client:
                create_url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts"
                resp = await client.post(create_url, json=create_payload, headers=headers, timeout=10.0)
                if resp.status_code in [200, 201]:
                    payload = resp.json()
                    contact_id = payload.get("payload", {}).get("contact", {}).get("id")
                    logger.info(f"Contacto creado en Chatwoot: ID {contact_id}")
                    return contact_id
                else:
                    logger.error(f"Error al crear contacto en Chatwoot: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Excepción en get_or_create_contact: {str(e)}")
        return None

    async def get_or_create_conversation(self, contact_id: int, inbox_id: Optional[int] = None) -> Optional[int]:
        """Busca una conversación abierta para el contacto o crea una nueva en el inbox."""
        if not self.is_configured:
            return None

        headers = self._get_headers()
        try:
            # 1. Buscar conversaciones del contacto
            async with httpx.AsyncClient() as client:
                convs_url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/{contact_id}/conversations"
                resp = await client.get(convs_url, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    convs = resp.json().get("payload", [])
                    # Retornar la última conversación abierta
                    open_convs = [c for c in convs if c.get("status") != "resolved"]
                    if open_convs:
                        conv_id = open_convs[0].get("id")
                        logger.info(f"Conversación abierta encontrada en Chatwoot: ID {conv_id}")
                        return conv_id

            # 2. Crear conversación
            target_inbox_id = inbox_id or self.inbox_id
            create_payload = {
                "inbox_id": target_inbox_id,
                "contact_id": contact_id,
                "status": "open"
            }
            async with httpx.AsyncClient() as client:
                create_url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"
                resp = await client.post(create_url, json=create_payload, headers=headers, timeout=10.0)
                if resp.status_code in [200, 201]:
                    conv_id = resp.json().get("id")
                    logger.info(f"Conversación creada en Chatwoot: ID {conv_id}")
                    return conv_id
                else:
                    logger.error(f"Error al crear conversación en Chatwoot: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Excepción en get_or_create_conversation: {str(e)}")
        return None

    async def post_message(self, conversation_id: int, content: str, is_private: bool = False, message_type: str = "incoming") -> bool:
        """Envía un mensaje o nota interna a la conversación de Chatwoot."""
        if not self.is_configured:
            return False

        headers = self._get_headers()
        payload = {
            "content": content,
            "message_type": message_type,
            "private": is_private
        }
        try:
            async with httpx.AsyncClient() as client:
                msg_url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
                resp = await client.post(msg_url, json=payload, headers=headers, timeout=10.0)
                if resp.status_code in [200, 201]:
                    return True
                else:
                    logger.error(f"Error al enviar mensaje a Chatwoot: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Excepción en post_message: {str(e)}")
        return False

    async def update_conversation_status(self, conversation_id: int, status: str) -> bool:
        """Actualiza el estado de una conversación en Chatwoot (open, resolved, snoozed, bot)."""
        if not self.is_configured:
            return False
        headers = self._get_headers()
        try:
            async with httpx.AsyncClient() as client:
                toggle_url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/toggle_status"
                resp = await client.post(toggle_url, json={"status": status}, headers=headers, timeout=5.0)
                return resp.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error actualizando estado en Chatwoot: {e}")
            return False

    async def post_bot_message(self, phone: str, content: str, phone_number_id: Optional[str] = None) -> bool:
        """Envía un mensaje de salida del bot a la conversación correspondiente en Chatwoot."""
        if not self.is_configured:
            return False
        try:
            inbox_id = None
            from app.config import settings
            mapping = settings.whatsapp_inbox_mapping or {}
            if phone_number_id and phone_number_id in mapping:
                inbox_id = mapping[phone_number_id].get("inbox_id")
            
            cw_contact_id = await self.get_or_create_contact(phone, f"Cliente +{phone}", inbox_id=inbox_id)
            if cw_contact_id:
                cw_conv_id = await self.get_or_create_conversation(cw_contact_id, inbox_id=inbox_id)
                if cw_conv_id:
                    return await self.post_message(cw_conv_id, content, message_type="outgoing")
        except Exception as e:
            logger.error(f"Error enviando mensaje saliente del bot a Chatwoot: {e}")
        return False
