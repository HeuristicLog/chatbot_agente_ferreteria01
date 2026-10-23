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
# FLUJOS PRINCIPALES AUTOMOTRICES (AutoEcuador Motors)
# ─────────────────────────────────────────────

async def send_welcome_menu(phone: str, internal_key: str, name: str = "", phone_number_id: Optional[str] = None):
    """Menú interactivo oficial con lista de categorías y opciones comerciales guiadas."""
    greeting = f"¡Hola{' ' + name if name else ''}! 😊"
    body = (
        f"{greeting} Te damos la bienvenida a *AutoEcuador Motors* 🇪🇨, tu concesionario multimarca oficial.\n\n"
        "Soy *Alex*, tu asesor comercial inteligente para vehículos nuevos y seminuevos 2026.\n\n"
        "Toca el botón *📋 Ver Opciones y Flujos* para desplegar nuestro menú interactivo y avanzar en tu consulta:"
    )
    sections = [
        {
            "title": "🚘 Tipo de Vehículo",
            "rows": [
                {"id": "auto_cat_hibridos", "title": "⚡ Híbridos / Eléctricos", "description": "Toyota Yaris Cross (0 Pico y Placa)"},
                {"id": "auto_cat_pickups",  "title": "🛻 Camionetas 4x4",         "description": "Chevrolet D-Max, Hilux, Poer para trabajo"},
                {"id": "auto_cat_suvs",     "title": "🚙 SUVs Familiares",        "description": "Sportage, Tucson, Tracker 2026"}
            ]
        },
        {
            "title": "💼 Crédito & Servicios",
            "rows": [
                {"id": "auto_flow_credito",   "title": "💰 Simulación de Crédito",  "description": "Entradas desde el 20% y plazos a 60m"},
                {"id": "auto_flow_retoma",    "title": "🔄 Plan Retoma (Usados)",   "description": "Tu auto usado como parte de pago"},
                {"id": "auto_flow_testdrive", "title": "🏎️ Agendar Test Drive",     "description": "Prueba de manejo sin costo a domicilio"},
                {"id": "flow_catalogo",       "title": "🚘 Vitrina & Cotizador",    "description": "Pantalla emergente con fotos reales"},
                {"id": "flow_asesor",         "title": "👨‍💼 Hablar con Asesor",     "description": "Atención humana en Quito Centro"}
            ]
        }
    ]
    await _send_list(
        phone=phone,
        body=body,
        button_text="📋 Ver Opciones y Flujos",
        sections=sections,
        header="🚗 AutoEcuador Motors 2026",
        footer="Concesionario Oficial Multimarca • Ecuador",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_pickups_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Flujo interactivo para Camionetas 4x4 y trabajo."""
    body = (
        "🛻 *Camionetas 4x4 en AutoEcuador Motors 2026:*\n\n"
        "1. *Chevrolet D-Max High Country 3.0L Diésel 4x4*\n"
        "• 💰 Precio: $34,990 | Entrada (20%): $6,998 | Cuota: $585/mes\n\n"
        "2. *Toyota Hilux Doble Cabina 2.4L Diésel 4x4*\n"
        "• 💰 Precio: $38,490 | Entrada (20%): $7,698 | Cuota: $645/mes\n\n"
        "3. *Great Wall Poer Luxury 2.0L Turbo Diésel 4x4*\n"
        "• 💰 Precio: $28,990 | Entrada (20%): $5,798 | Cuota: $485/mes\n\n"
        "¿Qué deseas hacer ahora? Selecciona una acción:"
    )
    buttons = [
        {"id": "flow_catalogo", "title": "🚘 Ver en Vitrina"},
        {"id": "auto_flow_credito", "title": "💰 Simular Cuotas"},
        {"id": "auto_td_pickups", "title": "🏎️ Test Drive 4x4"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="🛻 Pickups 4x4 Ecuador",
        footer="Garantía de fábrica y entrega inmediata",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_suvs_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Flujo interactivo para SUVs familiares."""
    body = (
        "🚙 *SUVs Familiares en AutoEcuador Motors 2026:*\n\n"
        "• *Chery Tiggo 4 Pro Luxury 1.5L Turbo:* $18,490 (Cuota: $310/mes)\n"
        "• *Kia Sonet LX 1.5L:* $19,990 (Cuota: $335/mes)\n"
        "• *Chevrolet Tracker RS 1.2L Turbo:* $22,990 (Cuota: $385/mes)\n"
        "• *Kia Sportage LX 2.0L Automático:* $26,490 (Cuota: $445/mes)\n"
        "• *Hyundai Tucson NX4 Advance:* $29,990 (Cuota: $505/mes)\n\n"
        "Todos con 6 airbags y amplio maletero para viajes familiares en Ecuador. ¿Cómo deseas continuar?"
    )
    buttons = [
        {"id": "flow_catalogo", "title": "🚘 Ver en Vitrina"},
        {"id": "auto_flow_credito", "title": "💰 Simular Cuotas"},
        {"id": "auto_td_suvs", "title": "🏎️ Test Drive SUV"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="🚙 SUVs Familiares 2026",
        footer="Plazos de 12 a 60 meses con banca nacional",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_hibridos_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Flujo interactivo para vehículos Híbridos y Eléctricos (0 Pico y Placa)."""
    body = (
        "⚡ *Movilidad Híbrida & Ecológica en AutoEcuador Motors:*\n\n"
        "🌿 *Toyota Yaris Cross Híbrido 1.5L (Modelo 2026)*\n"
        "• 💰 *Precio con IVA (15%):* $27,990 USD\n"
        "• 💵 *Entrada (20%):* $5,598 | 📊 *Cuota:* $465/mes\n"
        "• 🚀 *Ventaja Ecuador:* **CERO PICO Y PLACA en Quito todos los días**\n"
        "• ⛽ *Consumo:* Hasta 85 km por galón (auto-recargable, sin cables)\n"
        "• 🛡️ *Seguridad:* Toyota Safety Sense con frenado autónomo\n\n"
        "Elige tu siguiente paso:"
    )
    buttons = [
        {"id": "flow_catalogo", "title": "🚘 Ver Yaris Cross"},
        {"id": "auto_flow_credito", "title": "💰 Cuotas Híbrido"},
        {"id": "auto_td_hibridos", "title": "🏎️ Test Drive Híbrido"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="⚡ Cero Pico y Placa Quito",
        footer="Garantía de batería 8 años o 160.000 km",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_credito_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Flujo guiado para simulación de crédito por rango de entrada."""
    body = (
        "💰 *Asesoría de Financiamiento Automotriz 2026:*\n\n"
        "Trabajamos con Banco Pichincha, Banco Guayaquil, Produbanco y cooperativas aliadas con aprobación en 24 horas.\n\n"
        "¿De cuánto dispones aproximadamente para tu entrada inicial?"
    )
    buttons = [
        {"id": "auto_down_3to5", "title": "💰 $3.000 a $5.000"},
        {"id": "auto_down_5to8", "title": "💰 $5.000 a $8.000"},
        {"id": "auto_down_more8", "title": "💰 Más de $8.000"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="📊 Simulador de Crédito",
        footer="Tasa de interés automotriz preferencial",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_credito_range_result(phone: str, range_key: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra modelos y cuotas calculadas según el rango de entrada elegido."""
    if range_key == "auto_down_3to5":
        body = (
            "💰 *Para una Entrada de $3.000 a $5.000 USD:*\n\n"
            "Modelos recomendados con el 20% de entrada:\n"
            "• *Chery Tiggo 4 Pro Luxury:* Entrada $3,698 ➔ Cuota $310/mes\n"
            "• *Kia Sonet LX 1.5L:* Entrada $3,998 ➔ Cuota $335/mes\n"
            "• *Chevrolet Tracker RS Turbo:* Entrada $4,598 ➔ Cuota $385/mes\n\n"
            "¿Deseas verlos en la vitrina con fotos reales o agendar una prueba de manejo?"
        )
    elif range_key == "auto_down_5to8":
        body = (
            "💰 *Para una Entrada de $5.000 a $8.000 USD:*\n\n"
            "Modelos recomendados con el 20% de entrada:\n"
            "• *Toyota Yaris Cross Híbrido:* Entrada $5,598 ➔ Cuota $465/mes (0 Pico y Placa)\n"
            "• *Great Wall Poer 4x4:* Entrada $5,798 ➔ Cuota $485/mes\n"
            "• *Kia Sportage LX 2.0L:* Entrada $5,298 ➔ Cuota $445/mes\n"
            "• *Hyundai Tucson NX4:* Entrada $5,998 ➔ Cuota $505/mes\n"
            "• *Chevrolet D-Max 4x4 Diésel:* Entrada $6,998 ➔ Cuota $585/mes\n\n"
            "¿Cómo prefieres continuar?"
        )
    else:
        body = (
            "💰 *Para una Entrada Mayor a $8.000 USD:*\n\n"
            "Modelos recomendados de alta gama y tracción total 4x4:\n"
            "• *Chevrolet D-Max High Country 3.0L Diésel 4x4:* Entrada $6,998 ➔ Cuota $585/mes (con $10k baja a $490/mes)\n"
            "• *Toyota Hilux Doble Cabina 4x4:* Entrada $7,698 ➔ Cuota $645/mes (con $12k baja a $515/mes)\n\n"
            "¡A mayor entrada, tu cuota mensual se reduce drásticamente! ¿Qué paso deseas dar?"
        )
    
    buttons = [
        {"id": "flow_catalogo", "title": "🚘 Abrir Vitrina"},
        {"id": "auto_flow_testdrive", "title": "🏎️ Agendar Test Drive"},
        {"id": "flow_asesor", "title": "👨‍💼 Asesor de Crédito"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="📈 Comparativo Financiero",
        footer="Aprobación bancaria en 24h",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_retoma_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Flujo del Plan Retoma para entregar auto usado como parte de pago."""
    body = (
        "🔄 *Plan Retoma AutoEcuador Motors:*\n\n"
        "¡Recibimos tu auto usado de cualquier marca o año como parte de pago de tu nuevo 0 km!\n\n"
        "📌 *¿Cómo funciona?*\n"
        "1. Nuestro perito revisa el avalúo de tu auto.\n"
        "2. El valor acordado se descuenta directamente de la entrada del auto nuevo.\n"
        "3. Nos encargamos de todos los trámites legales y traspaso de dominio.\n\n"
        "¿Cómo deseas avanzar?"
    )
    buttons = [
        {"id": "flow_catalogo", "title": "🚘 Ver Modelos 2026"},
        {"id": "auto_flow_credito", "title": "💰 Simular Crédito"},
        {"id": "flow_asesor", "title": "👨‍💼 Hablar con Tasador"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="🔄 Plan Retoma de Usados",
        footer="Tasación transparente al mejor precio de mercado",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_testdrive_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Flujo para agendar Test Drive a domicilio o en showroom."""
    body = (
        "🏎️ *Agenda tu Test Drive en AutoEcuador Motors (100% Gratuito):*\n\n"
        "Prueba la potencia, suavidad y comodidad del vehículo antes de tomar tu decisión.\n\n"
        "¿Dónde prefieres realizar la prueba de manejo?"
    )
    buttons = [
        {"id": "auto_td_domicilio", "title": "🏠 A Domicilio"},
        {"id": "auto_td_showroom", "title": "📍 En Showroom Quito"},
        {"id": "flow_asesor", "title": "👨‍💼 Hablar con Asesor"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="🏎️ Prueba de Manejo Oficial",
        footer="Sin costo ni compromiso de compra",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def confirm_testdrive_preference(phone: str, preference: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Confirma la modalidad de Test Drive y conecta asesor."""
    import uuid
    lead_code = f"LEAD-AUTO-{uuid.uuid4().hex[:6].upper()}"
    pref_label = "A Domicilio (Casa / Oficina)" if "domicilio" in preference else "En Showroom Quito Centro"
    
    body = (
        f"🏎️ *¡Solicitud de Test Drive Registrada!*\n\n"
        f"📋 *Código:* `{lead_code}`\n"
        f"📍 *Modalidad:* {pref_label}\n\n"
        "👨‍💼 *Un asesor comercial se comunicará contigo por este mismo chat de WhatsApp* para coordinar el día, la hora y el modelo exacto que deseas probar.\n\n"
        "Mientras tanto, puedes seguir explorando las fichas técnicas en nuestra vitrina virtual:"
    )
    buttons = [
        {"id": "flow_catalogo", "title": "🚘 Ver en Vitrina"},
        {"id": "auto_flow_credito", "title": "💰 Simular Crédito"},
        {"id": "flow_asesor", "title": "👨‍💼 Hablar con Asesor"}
    ]
    await _send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header="✅ Prueba Agendada con Éxito",
        footer="AutoEcuador Motors • Quito Centro",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_main_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Menú principal para volver desde cualquier flujo."""
    import os
    clean_phone = phone.replace("+", "").replace(" ", "").strip()
    ngrok_url = os.getenv("CATALOG_BASE_URL", "https://usable-thorn-kabob.ngrok-free.dev")
    catalog_url = f"{ngrok_url}/catalogo-autos?phone={clean_phone}&sucursal=Centro"
    
    body = (
        "¿En qué más te puedo asesorar? 🚗✨\n\n"
        "Toca el botón para abrir la vitrina interactiva con fotos reales, simulación de crédito y tu garaje virtual:"
    )
    await _send_cta_url(
        phone=phone,
        body=body,
        display_text="🚘 Explorar Vitrina",
        url=catalog_url,
        header="🚗 AutoEcuador Motors",
        footer="AutoEcuador Motors • Asesoría 24/7",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_catalog_flow(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Alias para enviar el catálogo interactivo In-App Browser."""
    return await send_catalog_link(phone, internal_key, phone_number_id=phone_number_id)

async def send_catalog_link(phone: str, internal_key: str, phone_number_id: Optional[str] = None, sucursal: Optional[str] = "Centro"):
    """Envía el catálogo interactivo (In-App Browser Webview estilo Jelou.ia / Yalo)."""
    import os
    clean_phone = phone.replace("+", "").replace(" ", "").strip()
    ngrok_url = os.getenv("CATALOG_BASE_URL", "https://usable-thorn-kabob.ngrok-free.dev")
    catalog_url = f"{ngrok_url}/catalogo-autos?phone={clean_phone}&sucursal={sucursal or 'Centro'}"
    
    body = (
        "¡Bienvenido a la vitrina virtual de *AutoEcuador Motors* 🇪🇨! 🚘✨\n\n"
        "Toca el botón *🚘 Explorar Vitrina* para ver todos los vehículos 2026 con fotos reales, calcular tu cuota mensual y solicitar tu cotización formal sin salir de WhatsApp:"
    )
    
    await _send_cta_url(
        phone=phone,
        body=body,
        display_text="🚘 Explorar Vitrina",
        url=catalog_url,
        header="🚗 AutoEcuador Motors",
        footer="Concesionario Oficial • Financiamiento 24/7",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_faq_list(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Lista de categorías de preguntas frecuentes automotrices."""
    sections = [
        {
            "title": "📋 Consultas Frecuentes AutoEcuador",
            "rows": [
                {"id": "faq_financiamiento", "title": "💳 Crédito Vehicular",         "description": "Entradas, plazos y bancos aliados"},
                {"id": "faq_retoma",         "title": "🔄 Plan Retoma (Usados)",      "description": "Recibimos tu auto como parte de pago"},
                {"id": "faq_hibridos",       "title": "⚡ Híbridos y Pico y Placa",   "description": "Exención de restricción y ahorro"},
                {"id": "faq_garantia",       "title": "🛡️ Garantía de Fábrica",       "description": "Hasta 10 años o 160.000 km"},
                {"id": "faq_testdrive",      "title": "🏎️ Test Drive a Domicilio",    "description": "Prueba de manejo sin costo"},
                {"id": "faq_ubicacion",      "title": "📍 Showrooms y Concesionarios","description": "Quito, Guayaquil, Cuenca y Ambato"},
            ]
        }
    ]
    await _send_list(
        phone=phone,
        body="Selecciona la categoría automotriz sobre la que deseas información y te respondo al instante:",
        button_text="Ver opciones",
        sections=sections,
        header="❓ Asesoría Comercial AutoEcuador",
        footer="Toca una opción para ver los detalles",
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
    """Responde una consulta automotriz específica."""
    answers = {
        "faq_financiamiento": (
            "💳 *Crédito Vehicular AutoEcuador Motors*\n\n"
            "• *Entrada mínima:* Desde el *20%* del valor del vehículo\n"
            "• *Plazos de financiamiento:* De *12 hasta 72 meses*\n"
            "• *Bancos y Cooperativas Aliadas:* Banco Pichincha, Banco Guayaquil, Produbanco, Coop. JEP, Coop. Policía Nacional\n"
            "• *Tiempo de pre-aprobación:* Menos de *24 horas hábiles* con solo tu cédula y planilla de servicios\n"
            "• *Tasa preferencial:* Desde 12.99% anual fija"
        ),
        "faq_retoma": (
            "🔄 *Plan Retoma de Vehículos Usados*\n\n"
            "¡Aceptamos tu auto actual como parte de pago de tu 0 km!\n\n"
            "• *Avalúo técnico sin costo:* En cualquiera de nuestros talleres o a domicilio en menos de 2 horas\n"
            "• *Precio comercial justo:* Pagamos el valor real de mercado ecuatoriano\n"
            "• *Trámite ágil:* Nosotros gestionamos el contrato, traspaso y levantamiento de gravámenes\n"
            "• El monto acordado se deduce de inmediato de la entrada de tu nuevo auto."
        ),
        "faq_hibridos": (
            "⚡ *Beneficios de Vehículos Híbridos en Ecuador*\n\n"
            "• 🚫 *Cero Pico y Placa:* Circulas todos los días y a toda hora sin restricción en Quito y Guayaquil\n"
            "• ⛽ *Ahorro de combustible:* Hasta *75 km por galón* (ahorro de más del 60% frente a motores convencionales)\n"
            "• 🔋 *Auto-recargable:* La batería se regenera automáticamente al frenar, ¡no requiere enchufarse!\n"
            "• 💰 *Beneficio tributario:* 0% de aranceles de importación"
        ),
        "faq_garantia": (
            "🛡️ *Garantía Oficial de Fábrica*\n\n"
            "• *Cobertura extendida:* Hasta *10 años o 160.000 km* (según la marca del modelo)\n"
            "• *Red nacional de talleres:* Mantenimiento preventivo en Quito, Guayaquil, Cuenca, Manta, Ambato y Loja\n"
            "• *Repuestos 100% genuinos:* Stock permanente de fábrica y auxilio mecánico 24/7 en carretera"
        ),
        "faq_testdrive": (
            "🏎️ *Test Drive (Prueba de Manejo)*\n\n"
            "• Prueba el vehículo de tus sueños antes de tomar una decisión\n"
            "• *Modalidad:* En concesionario o *a domicilio* (te llevamos el auto a tu casa u oficina)\n"
            "• *Sin costo ni compromiso*\n"
            "• *Requisitos:* Licencia de conducir vigente y cédula"
        ),
        "faq_ubicacion": (
            "📍 *Red de Concesionarios y Showrooms AutoEcuador*\n\n"
            "🏢 *Quito Norte:* Av. Los Granados y 6 de Diciembre\n"
            "🏢 *Quito Sur:* Av. Maldonado y Morán Valverde\n"
            "🏢 *Guayaquil:* Av. Juan Tanca Marengo Km 2.5\n"
            "🏢 *Cuenca:* Av. España y Huayna Cápac\n"
            "🏢 *Ambato:* Av. Atahualpa y Los Chasquis\n\n"
            "🕒 *Horario:* Lunes a Viernes 08h30 a 18h30 | Sábados 09h00 a 16h00"
        ),
    }
    
    answer = answers.get(faq_id, "❓ Lo siento, no tengo información sobre esa consulta en este momento.")
    
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
        footer="AutoEcuador Motors • Asesor Virtual",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )
