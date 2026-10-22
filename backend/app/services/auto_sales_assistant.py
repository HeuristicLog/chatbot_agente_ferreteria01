"""
Auto Sales Assistant — Executive AI Sales Consultant for AutoEcuador Motors (2026)
Processes customer questions about vehicle models, pricing, financing, trade-ins, and test drives,
pulling real-time data from PostgreSQL and presenting rich interactive WhatsApp responses with in-app browser links.
"""
import logging
import os
import re
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.tables import Vehicle, VehicleCartItem, VehicleQuote
from app.services import interactive_flow_service as flows

logger = logging.getLogger("backend.services.auto_sales")

async def process_auto_sales_message(
    phone: str,
    message: str,
    db: AsyncSession,
    redis_client: Any,
    internal_key: str,
    phone_number_id: Optional[str] = None
) -> bool:
    """
    Analiza el mensaje del cliente con mentalidad de ejecutivo de ventas automotriz.
    Si detecta intención de compra, consulta de modelos, precios, crédito o test drive,
    formula una respuesta comercial personalizada y devuelve True.
    """
    clean = message.lower().strip()
    clean_phone = phone.replace("+", "").replace(" ", "").strip()
    ngrok_url = os.getenv("CATALOG_BASE_URL", "https://usable-thorn-kabob.ngrok-free.dev")
    catalog_url = f"{ngrok_url}/catalogo-autos?phone={clean_phone}"

    # 1. Intención: Camionetas / Pickups / 4x4
    pickup_keywords = ["camioneta", "camionetas", "pickup", "pick up", "pick-up", "4x4", "dmax", "d-max", "hilux", "poer", "doble cabina", "balde", "carga", "trabajo pesado"]
    if any(k in clean for k in pickup_keywords):
        query = select(Vehicle).where(
            Vehicle.is_active == True,
            (Vehicle.body_type.ilike("%Pickup%")) | (Vehicle.traction.ilike("%4x4%"))
        ).order_by(Vehicle.price_usd.asc())
        res = await db.execute(query)
        vehicles = res.scalars().all()

        if vehicles:
            lines = [
                "🚗 *Camionetas 4x4 Disponibles en AutoEcuador Motors 2026:*\n",
                "Ideales para trabajo duro, haciendas, construcción y viajes en todo el país con tracción total:\n"
            ]
            for i, v in enumerate(vehicles, 1):
                price_fmt = f"${float(v.price_usd):,.0f}"
                down_fmt = f"${float(v.min_down_payment):,.0f}"
                month_fmt = f"${float(v.estimated_monthly_fee):,.0f}"
                lines.append(
                    f"*{i}. {v.brand} {v.model}*\n"
                    f"• 💰 *Precio con IVA (15%):* {price_fmt} USD\n"
                    f"• 💵 *Entrada (20%):* {down_fmt} | 📊 *Cuota:* {month_fmt}/mes (60m)\n"
                    f"• ⚙️ *Motor:* {v.engine} • Tracción: {v.traction}\n"
                    f"• 📦 *Carga:* {v.trunk_capacity_liters} kg • Stock: {v.stock_units} unidades\n"
                )
            lines.append("Toca el botón abajo para ver las fotos reales, fichas técnicas y simular tu crédito en vivo:")
            
            await flows._send_cta_url(
                phone=phone,
                body="\n".join(lines),
                display_text="🚘 Ver Camionetas 4x4",
                url=catalog_url,
                header="🛻 Camionetas 4x4 Ecuador",
                footer="Aprobación de crédito en 24h",
                internal_key=internal_key,
                phone_number_id=phone_number_id
            )
            return True

    # 2. Intención: Híbridos / Pico y Placa
    hybrid_keywords = ["hibrido", "híbrido", "hibridos", "híbridos", "pico y placa", "pico y placa quito", "ecologico", "electrico", "eléctrico", "gasolina ahorro"]
    if any(k in clean for k in hybrid_keywords):
        query = select(Vehicle).where(Vehicle.is_active == True, Vehicle.fuel_type.ilike("%Híbrido%"))
        res = await db.execute(query)
        vehicles = res.scalars().all()

        lines = [
            "⚡ *Vehículos Híbridos en AutoEcuador Motors (Cero Pico y Placa)* 🌿\n",
            "Nuestros modelos híbridos auto-recargables no necesitan enchufes y circulan *todos los días sin restricción vehicular* en Quito y Guayaquil:\n"
        ]
        for v in vehicles:
            price_fmt = f"${float(v.price_usd):,.0f}"
            down_fmt = f"${float(v.min_down_payment):,.0f}"
            month_fmt = f"${float(v.estimated_monthly_fee):,.0f}"
            lines.append(
                f"🚘 *{v.brand} {v.model} ({v.year})*\n"
                f"• 💰 *Precio de lista:* {price_fmt} USD (Inc. IVA)\n"
                f"• 💵 *Entrada (20%):* {down_fmt} | 📊 *Cuota:* {month_fmt}/mes\n"
                f"• ⛽ *Rendimiento:* Hasta *75 km por galón*\n"
                f"• 🛡️ *Seguridad:* Toyota Safety Sense con frenado autónomo\n"
            )
        lines.append("Toca el botón para ver la ficha técnica completa y cotizar:")
        await flows._send_cta_url(
            phone=phone,
            body="\n".join(lines),
            display_text="⚡ Ver Autos Híbridos",
            url=catalog_url,
            header="⚡ Autos Híbridos Ecuador",
            footer="Exento de Pico y Placa • Ahorro 75 km/gal",
            internal_key=internal_key,
            phone_number_id=phone_number_id
        )
        return True

    # 3. Intención: SUVs Familiares / Compactos
    suv_keywords = ["suv", "suvs", "familiar", "sportage", "tracker", "sonet", "tucson", "creta", "tiggo", "viaje"]
    if any(k in clean for k in suv_keywords):
        query = select(Vehicle).where(Vehicle.is_active == True, Vehicle.body_type == "SUV").order_by(Vehicle.price_usd.asc())
        res = await db.execute(query)
        vehicles = res.scalars().all()

        lines = [
            "🚙 *Los SUVs Más Vendidos de Ecuador en AutoEcuador Motors:*\n",
            "Modelos familiares con el mayor espacio, seguridad 5 estrellas y cuotas accesibles:\n"
        ]
        for v in vehicles[:4]:
            price_fmt = f"${float(v.price_usd):,.0f}"
            down_fmt = f"${float(v.min_down_payment):,.0f}"
            month_fmt = f"${float(v.estimated_monthly_fee):,.0f}"
            lines.append(
                f"• *{v.brand} {v.model}:* {price_fmt} (Entrada: {down_fmt} | Cuota: {month_fmt}/mes)"
            )
        lines.append("\nTodos con 6+ airbags, control de estabilidad y pantalla táctil inalámbrica.\nToca abajo para explorar la vitrina con fotos reales:")
        await flows._send_cta_url(
            phone=phone,
            body="\n".join(lines),
            display_text="🚙 Ver Todos los SUVs",
            url=catalog_url,
            header="🚙 SUVs Familiares Ecuador",
            footer="Garantía de hasta 10 años",
            internal_key=internal_key,
            phone_number_id=phone_number_id
        )
        return True

    # 4. Intención: Presupuesto / Consulta de Entrada (ej. "tengo 5000", "cuánto de entrada")
    budget_match = re.search(r'(\d{1,2})[\.,]?(\d{3})', clean)
    if "entrada" in clean or "presupuesto" in clean or "alcanza" in clean or budget_match:
        budget = 5000.0
        if budget_match:
            try:
                budget = float(budget_match.group(1) + budget_match.group(2))
            except Exception:
                budget = 5000.0

        query = select(Vehicle).where(Vehicle.is_active == True, Vehicle.min_down_payment <= budget).order_by(Vehicle.price_usd.asc())
        res = await db.execute(query)
        matches = res.scalars().all()

        if matches:
            lines = [
                f"💰 *Opciones para tu Entrada de aprox. ${budget:,.0f} USD:*\n",
                "Con tu presupuesto de entrada puedes estrenar cualquiera de estos vehículos inmediatamente:\n"
            ]
            for m in matches[:4]:
                price_fmt = f"${float(m.price_usd):,.0f}"
                down_fmt = f"${float(m.min_down_payment):,.0f}"
                month_fmt = f"${float(m.estimated_monthly_fee):,.0f}"
                lines.append(f"• *{m.brand} {m.model}* ({price_fmt}): Entrada desde {down_fmt} | Cuota estimada: {month_fmt}/mes")
            lines.append("\nPuedes ajustar el plazo y la cuota exacta en nuestro simulador en vivo:")
            await flows._send_cta_url(
                phone=phone,
                body="\n".join(lines),
                display_text="🧮 Simular Mi Cuota",
                url=catalog_url,
                header="🧮 Financiamiento a Tu Medida",
                footer="Aprobación 24h sin garante",
                internal_key=internal_key,
                phone_number_id=phone_number_id
            )
            return True

    # 5. Intención: Mi Garaje / Carrito
    if "garaje" in clean or "mi garaje" in clean or "cotizaciones" in clean:
        query = select(VehicleCartItem, Vehicle).join(Vehicle, VehicleCartItem.vehicle_id == Vehicle.id).where(
            VehicleCartItem.customer_phone == clean_phone,
            VehicleCartItem.status == "in_cart"
        )
        res = await db.execute(query)
        items = res.all()

        if items:
            lines = [f"🏠 *Tu Garaje Virtual ({len(items)} vehículo(s) guardados):*\n"]
            for cart_item, v in items:
                lines.append(
                    f"• *{v.brand} {v.model}* (${float(v.price_usd):,.0f})\n"
                    f"  Entrada: ${float(cart_item.down_payment_amount):,.0f} | Cuota: ${float(cart_item.estimated_monthly_fee):,.0f}/mes ({cart_item.term_months}m)\n"
                )
            lines.append("Toca el botón para abrir tu garaje y finalizar tu solicitud de crédito:")
            await flows._send_cta_url(
                phone=phone,
                body="\n".join(lines),
                display_text="🚘 Abrir Mi Garaje",
                url=catalog_url,
                header="🏠 Mi Garaje AutoEcuador",
                footer="Vehículos listos para cotizar",
                internal_key=internal_key,
                phone_number_id=phone_number_id
            )
            return True
        else:
            msg = (
                "🏠 *Tu Garaje Virtual está listo.*\n\n"
                "Aún no has guardado vehículos. Abre nuestra vitrina virtual para explorar los modelos 2026, calcular tus cuotas y agregarlos a tu garaje:"
            )
            await flows._send_cta_url(
                phone=phone,
                body=msg,
                display_text="🚘 Explorar Vitrina",
                url=catalog_url,
                header="🏠 AutoEcuador Motors",
                footer="Modelos 2026 • Entrega Inmediata",
                internal_key=internal_key,
                phone_number_id=phone_number_id
            )
            return True

    # 6. Intención: Test Drive / Prueba de Manejo
    testdrive_keywords = ["test drive", "testdrive", "prueba de manejo", "manejar", "probar el carro", "probar el auto", "agendar prueba"]
    if any(k in clean for k in testdrive_keywords):
        msg = (
            "🏎️ *Agenda tu Prueba de Manejo (Test Drive)*\n\n"
            "Conoce la potencia, confort y tecnología de tu próximo vehículo.\n\n"
            "• *Opciones:* En nuestros showrooms o *a domicilio* (en tu casa u oficina).\n"
            "• *Ciudades:* Quito, Guayaquil, Cuenca, Ambato, Manta.\n"
            "• *Requisitos:* Licencia de conducir vigente y cédula.\n\n"
            "Toca el botón para elegir el modelo que deseas probar y la fecha de tu preferencia:"
        )
        await flows._send_cta_url(
            phone=phone,
            body=msg,
            display_text="🏎️ Elegir Modelo para Test Drive",
            url=catalog_url,
            header="🏎️ Test Drive AutoEcuador",
            footer="Prueba 100% gratuita y sin compromiso",
            internal_key=internal_key,
            phone_number_id=phone_number_id
        )
        return True

    # 7. Intención: Retoma de Auto Usado
    tradein_keywords = ["retoma", "usado", "auto usado", "reciben usado", "parte de pago", "avaluo", "avalúo", "mi carro usado"]
    if any(k in clean for k in tradein_keywords):
        msg = (
            "🔄 *Plan Retoma AutoEcuador Motors*\n\n"
            "¡Recibimos tu vehículo usado como parte de pago de tu 0 km!\n\n"
            "• *Avalúo comercial justo:* Pagamos el mejor precio del mercado ecuatoriano.\n"
            "• *Trámite 100% seguro:* Nosotros nos encargamos de los contratos y notaría.\n"
            "• El valor acordado se aplica inmediatamente a la *entrada de tu auto nuevo*.\n\n"
            "Abre la vitrina para simular tu nuevo modelo marcando la opción *'Deseo entregar mi auto usado'*"
        )
        await flows._send_cta_url(
            phone=phone,
            body=msg,
            display_text="🔄 Cotizar con Mi Usado",
            url=catalog_url,
            header="🔄 Plan Retoma Multimarca",
            footer="Inspección mecánica sin costo",
            internal_key=internal_key,
            phone_number_id=phone_number_id
        )
        return True

    return False
