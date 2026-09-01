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

# ─────────────────────────────────────────────
# HELPERS — Enviar mensajes al Gateway
# ─────────────────────────────────────────────

async def _send(phone: str, message: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Envía un mensaje de texto simple."""
    # Sincronizar salida de texto del bot con Chatwoot
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            await chatwoot.post_bot_message(phone, message, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando salida de texto del bot con Chatwoot en _send: {cw_err}")

    headers = {"X-Internal-API-Key": internal_key}
    payload = {"phone": phone, "message": message}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")
            
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GATEWAY_URL}/send",
            json=payload,
            headers=headers,
            timeout=10.0
        )

async def _send_buttons(phone: str, body: str, buttons: list, header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje con botones interactivos."""
    # Sincronizar botones del bot con Chatwoot
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            text = body
            if buttons:
                text += "\n\n" + "\n".join([f"[Botón: {b.get('title')}]" for b in buttons])
            await chatwoot.post_bot_message(phone, text, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando botones del bot con Chatwoot en _send_buttons: {cw_err}")

    headers = {"X-Internal-API-Key": internal_key}
    payload = {"phone": phone, "body": body, "buttons": buttons, "header": header, "footer": footer}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GATEWAY_URL}/send/buttons",
            json=payload,
            headers=headers,
            timeout=10.0
        )

async def _send_list(phone: str, body: str, button_text: str, sections: list, header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje con lista de opciones."""
    # Sincronizar listas del bot con Chatwoot
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            text = body
            if sections:
                text += "\n\n" + "\n".join([f"[Opción: {row.get('title')}]" for sec in sections for row in sec.get('rows', [])])
            await chatwoot.post_bot_message(phone, text, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando lista del bot con Chatwoot en _send_list: {cw_err}")

    headers = {"X-Internal-API-Key": internal_key}
    payload = {"phone": phone, "body": body, "button_text": button_text, "sections": sections, "header": header, "footer": footer}
    if phone_number_id:
        payload["phone_number_id"] = phone_number_id
        from app.config import settings
        mapping = settings.whatsapp_inbox_mapping or {}
        if phone_number_id in mapping:
            payload["access_token"] = mapping[phone_number_id].get("access_token")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GATEWAY_URL}/send/list",
            json=payload,
            headers=headers,
            timeout=10.0
        )

async def _send_cta_url(phone: str, body: str, display_text: str, url: str, header: str = "", footer: str = "", internal_key: str = "change_me", phone_number_id: Optional[str] = None):
    """Envía mensaje interactivo con botón CTA URL que abre la Webview emergente directamente dentro de WhatsApp."""
    try:
        from app.services.chatwoot_service import ChatwootService
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            text = f"{body}\n\n[Botón: {display_text} -> {url}]"
            await chatwoot.post_bot_message(phone, text, phone_number_id)
    except Exception as cw_err:
        logger.error(f"Error sincronizando CTA URL con Chatwoot: {cw_err}")

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

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GATEWAY_URL}/send/cta_url",
            json=payload,
            headers=headers,
            timeout=10.0
        )

# ─────────────────────────────────────────────
# FLUJOS PRINCIPALES
# ─────────────────────────────────────────────

async def send_welcome_menu(phone: str, internal_key: str, name: str = "", phone_number_id: Optional[str] = None):
    """Menú de bienvenida con los 3 botones principales."""
    greeting = f"¡Hola{' ' + name if name else ''}! 😊" 
    body = (
        f"{greeting} Soy *Castor* 🦫, el asistente virtual de *Ferretería Castor*.\n\n"
        "Estoy aquí para ayudarte con nuestro catálogo interactivo, pedidos y asesoría. ¿Qué necesitas hoy?"
    )
    buttons = [
        {"id": "flow_catalogo",  "title": "🛍️ Catálogo y Carrito"},
        {"id": "flow_pedido",    "title": "📦 Mi pedido"},
        {"id": "flow_asesor",    "title": "👨‍💼 Hablar con asesor"},
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Ferretería Castor • Atención 24/7",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_main_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Menú principal para volver desde cualquier flujo."""
    body = "¿En qué más te puedo ayudar? Elige una opción:"
    buttons = [
        {"id": "flow_catalogo",  "title": "🛍️ Catálogo y Carrito"},
        {"id": "flow_pedido",    "title": "📦 Mi pedido"},
        {"id": "flow_asesor",    "title": "👨‍💼 Hablar con asesor"},
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Ferretería Castor",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_catalog_link(phone: str, internal_key: str, phone_number_id: Optional[str] = None, sucursal: Optional[str] = "Centro"):
    """Envía la tarjeta interactiva con botón CTA URL que abre la tienda emergente dentro de WhatsApp."""
    import os
    base_url = os.getenv("PUBLIC_URL") or "https://usable-thorn-kabob.ngrok-free.dev"
    catalog_url = f"{base_url}/catalogo?phone={phone}&sucursal={sucursal or 'Centro'}"
    
    body = (
        "¡Bienvenido a la tienda virtual de *Ferretería Castor*! 🦫\n\n"
        "Toca el botón *Abrir Catálogo* aquí abajo para ver nuestra tienda interactiva: productos con fotos, buscador en vivo, selector `[− 0 +]` y carrito de compras sin salir de WhatsApp."
    )
    await _send_cta_url(
        phone=phone,
        body=body,
        display_text="🛍️ Abrir Catálogo",
        url=catalog_url,
        header="🛠️ Ferretería Castor",
        footer="Tienda Oficial • Compras en WhatsApp",
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
            # 2. Fallback a operación logística legacy
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
                    "Verifica el número de orden (ej. *CAST-2026-1042*) e inténtalo de nuevo, o contacta a un asesor si el problema persiste."
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
