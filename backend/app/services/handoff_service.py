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
            if conv.status in ["active", "bot_active"]:
                conv.status = "handed_over" if not conv.current_seller_id else "assigned"
                self.db.add(conv)
                await self.db.commit()
            return active, (conv.current_seller_id is not None)
            
        # Fetch context history (last 5 messages)
        history_text = "No hay mensajes recientes de contexto."
        try:
            recent_msgs = await self.conv_repo.get_recent_messages(conv.id, limit=5)
            if recent_msgs:
                history_lines = []
                for msg in recent_msgs:
                    role_label = "Cliente" if msg.role == "user" else "Asistente"
                    history_lines.append(f"- *{role_label}*: {msg.content.strip()}")
                history_text = "\n".join(history_lines)
        except Exception as history_err:
            logger.error(f"Error fetching history for handoff context: {history_err}")

        # 4. Create handoff entry
        metadata = {
            "ticket_id": ticket_id,
            "operation_id": operation_id,
            "phone_original": phone,
            "sucursal": sucursal,
            "phone_number_id": phone_number_id,
            "context_history": history_text
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
                        note_text = (
                            f"🤖 *Ferretería Bot Handoff* 🤖\n\n"
                            f"• *Sucursal:* {sucursal or 'No especificada'}\n"
                            f"• *Motivo:* {reason or 'No especificado'}\n"
                            f"• *Resumen:* {summary or 'No especificado'}\n\n"
                            f"💬 *Últimos 5 mensajes de contexto:*\n{history_text}"
                        )
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

                # Notificar al Asesor en su WhatsApp
                try:
                    if assigned_seller.whatsapp_phone:
                        msg_advisor = (
                            f"🔔 *NUEVA ASIGNACIÓN DE CLIENTE* 🔔\n\n"
                            f"• *Cliente:* +{phone}\n"
                            f"• *Sucursal:* {sucursal or 'General'}\n"
                            f"• *Motivo:* {reason or 'Solicitud de atención'}\n\n"
                            f"💬 *Últimos 5 mensajes de contexto:*\n{history_text}\n\n"
                            f"_El cliente está esperando. Por favor, atiende el chat desde Chatwoot._"
                        )
                        await self._send_gateway_message(assigned_seller.whatsapp_phone, msg_advisor)
                except Exception as notify_err:
                    logger.error(f"Error notifying seller on WhatsApp: {notify_err}")
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
