import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repository import AuditRepository
from app.repositories.conversation_repository import ConversationRepository
from app.services.session_service import SessionService
from app.services.chatwoot_service import ChatwootService
from app.db.tables import Handoff

logger = logging.getLogger("chatbot-api.services.handoff")

class HandoffService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_repo = AuditRepository(db)
        self.conv_repo = ConversationRepository(db)

    async def request_handoff(
        self,
        session_id: str,
        phone: str,
        reason: Optional[str] = None,
        summary: Optional[str] = None,
        ticket_id: Optional[int] = None,
        operation_id: Optional[int] = None,
        sucursal: Optional[str] = None,
        phone_number_id: Optional[str] = None
    ) -> Tuple[Handoff, bool]:
        """Flags the conversation as handed over and creates a handoff ticket for agent review."""
        # 1. Resolve inbox_id and sucursal using mapping if phone_number_id is provided
        inbox_id = None
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id and phone_number_id in mapping:
            inbox_id = mapping[phone_number_id].get("inbox_id")
            if not sucursal:
                sucursal = mapping[phone_number_id].get("sucursal")

        logger.info(f"Handoff requested for session {session_id}. Reason: {reason}, Sucursal: {sucursal}, PhoneID: {phone_number_id}, InboxID: {inbox_id}")
        
        # 2. Retrieve the conversation
        conv = await self.conv_repo.get_by_session_id(session_id)
        if not conv:
            # Fallback: create conversation
            phone_hash = SessionService.derive_phone_hash(phone)
            conv = await self.conv_repo.create(session_id, phone_hash)
            
        # 3. Check if there is already an active handoff
        active = await self.audit_repo.get_active_handoff(conv.id)
        if active:
            logger.info(f"An active handoff already exists for conversation {conv.id}. Re-using.")
            return active, (conv.current_seller_id is not None)
            
        # 4. Create handoff entry
        metadata = {
            "ticket_id": ticket_id,
            "operation_id": operation_id,
            "phone_original": phone,
            "sucursal": sucursal,
            "phone_number_id": phone_number_id
        }
        
        # Sincronizar con Chatwoot si está configurado
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            try:
                cw_contact_id = await chatwoot.get_or_create_contact(phone, f"Cliente +{phone}", inbox_id=inbox_id)
                if cw_contact_id:
                    cw_conv_id = await chatwoot.get_or_create_conversation(cw_contact_id, inbox_id=inbox_id)
                    if cw_conv_id:
                        metadata["chatwoot_conversation_id"] = cw_conv_id
                        # Cambiar el estado a "open" en Chatwoot para que aparezca al agente
                        await chatwoot.update_conversation_status(cw_conv_id, "open")
                        # Enviar nota privada con el resumen para el agente
                        note_text = f"🤖 *Ferretería Bot Handoff* 🤖\n\n• *Sucursal:* {sucursal or 'No especificada'}\n• *Motivo:* {reason or 'No especificado'}\n• *Resumen:* {summary or 'No especificado'}"
                        await chatwoot.post_message(cw_conv_id, note_text, is_private=True)
            except Exception as cw_err:
                logger.error(f"Error sincronizando con Chatwoot: {cw_err}")
 
        handoff = await self.audit_repo.create_handoff(
            conversation_id=conv.id,
            phone_hash=conv.phone_hash,
            reason=reason,
            summary=summary,
            metadata=metadata
        )
        
        # 5. Set conversation status to active/handed_over
        conv.status = "handed_over"
        self.db.add(conv)
        await self.db.commit()

        # 6. Asignar automáticamente un asesor y enviar notificaciones
        assigned_seller = None
        try:
            from app.services.assignment_service import AssignmentService
            assign_service = AssignmentService(self.db)
            assigned_seller = await assign_service.assign_conversation_to_seller(conv.id, sucursal=sucursal)
            
            if assigned_seller:
                logger.info(f"Handoff asignado automáticamente a: {assigned_seller.name} (+{assigned_seller.whatsapp_phone})")
                
                # Notificar al Cliente en su WhatsApp
                msg_client = (
                    f"✅ Un asesor de la *Sucursal {sucursal or 'General'}* ha tomado tu caso.\n"
                    f"👨‍💼 Te atiende: *{assigned_seller.name}*.\n"
                    f"En un momento se comunicará contigo."
                )
                await self._send_gateway_message(phone, msg_client)
            else:
                logger.warning(f"No hay asesores disponibles en este momento para la sucursal: {sucursal}")
                msg_client = (
                    f"🕒 Todos nuestros asesores de la *Sucursal {sucursal or 'General'}* están ocupados en este momento.\n\n"
                    f"Te hemos puesto en la fila de atención. Pronto uno de ellos tomará tu caso."
                )
                await self._send_gateway_message(phone, msg_client)
        except Exception as assign_err:
            logger.error(f"Error al asignar asesor en handoff: {assign_err}")
            
        return handoff, (assigned_seller is not None)

    async def _send_gateway_message(self, phone: str, message: str):
        from app.config import settings
        import httpx
        headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}
        import os
        gateway_url = os.getenv("WHATSAPP_GATEWAY_URL") or "http://whatsapp-gateway:8090"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{gateway_url}/send", json={"phone": phone, "message": message}, headers=headers, timeout=10.0)
        except Exception as e:
            logger.error(f"Failed to send message to gateway for {phone}: {e}")
