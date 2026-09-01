"""
In-Chat Native Commerce & Shopping Cart Service
Permite a los usuarios de WhatsApp navegar categorías, seleccionar productos,
gestionar su carrito de compras y confirmar pedidos 100% dentro del chat de WhatsApp,
sin abrir enlaces externos ni salir de la conversación.
"""

import json
import logging
import random
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.tables import Product, Order, OrderItem
from app.db.session import async_session
from app.services.session_service import SessionService
from app.services.chatwoot_service import ChatwootService
from app.services import interactive_flow_service as flows

logger = logging.getLogger("chatbot-api.services.in_chat_cart")

# ─── GESTIÓN DE CARRITO EN REDIS ────────────────────────────────

CART_KEY_PREFIX = "whatsapp_cart:"
CART_TTL_SECONDS = 86400  # 24 horas

async def get_cart(redis_client: Any, phone: str) -> Dict[str, Any]:
    """Obtiene el carrito activo del usuario desde Redis."""
    try:
        raw = await redis_client.get(f"{CART_KEY_PREFIX}{phone}")
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Error reading cart for {phone}: {e}")
    return {"items": {}, "customer_name": "Cliente WhatsApp", "delivery_type": "pickup", "sucursal": "Centro", "address": None}

async def save_cart(redis_client: Any, phone: str, cart_data: Dict[str, Any]):
    """Guarda el estado del carrito en Redis."""
    try:
        await redis_client.setex(f"{CART_KEY_PREFIX}{phone}", CART_TTL_SECONDS, json.dumps(cart_data))
    except Exception as e:
        logger.error(f"Error saving cart for {phone}: {e}")

async def clear_cart(redis_client: Any, phone: str):
    """Vacía el carrito del usuario."""
    try:
        await redis_client.delete(f"{CART_KEY_PREFIX}{phone}")
    except Exception as e:
        logger.error(f"Error clearing cart for {phone}: {e}")

async def add_item_to_cart(redis_client: Any, phone: str, sku: str, quantity: int = 1) -> Optional[Dict[str, Any]]:
    """Agrega un producto al carrito y devuelve el producto y resumen."""
    async with async_session() as session:
        stmt = select(Product).where(Product.sku == sku, Product.is_active == True)
        res = await session.execute(stmt)
        product = res.scalar_one_or_none()
        
        if not product:
            return None

        cart = await get_cart(redis_client, phone)
        items = cart.get("items", {})

        current_qty = items.get(sku, {}).get("quantity", 0)
        new_qty = current_qty + quantity

        items[sku] = {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "price": float(product.price),
            "quantity": new_qty,
            "subtotal": float(product.price * new_qty)
        }
        cart["items"] = items
        await save_cart(redis_client, phone, cart)
        return {"product": product, "quantity": new_qty, "cart": cart}

# ─── MENSAJES INTERACTIVOS NATIVOS ──────────────────────────────

async def send_categories_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra el catálogo nativo organizado por categorías en WhatsApp."""
    sections = [
        {
            "title": "📦 Departamentos de Ferretería",
            "rows": [
                {
                    "id": "cat_herramientas_elec",
                    "title": "⚡ Herramientas Eléctricas",
                    "description": "Taladros, amoladoras, rotomartillos, sierras"
                },
                {
                    "id": "cat_herramientas_man",
                    "title": "🔧 Herramientas Manuales",
                    "description": "Juegos de llaves, martillos, flexómetros"
                },
                {
                    "id": "cat_construccion",
                    "title": "🧱 Construcción y Obra",
                    "description": "Cemento Selvalegre, varillas, palas, carretillas"
                },
                {
                    "id": "cat_pinturas",
                    "title": "🎨 Pinturas y Acabados",
                    "description": "Látex Vinilac, anticorrosivos, rodillos"
                },
                {
                    "id": "cat_plomeria",
                    "title": "🚿 Plomería y Tuberías",
                    "description": "Tubos PVC, grifería FV, bombas de agua"
                },
                {
                    "id": "cat_electricidad",
                    "title": "💡 Electricidad e Iluminación",
                    "description": "Cables, focos LED, tomacorrientes Bticino"
                }
            ]
        },
        {
            "title": "🛒 Opciones de Compra",
            "rows": [
                {
                    "id": "cart_view",
                    "title": "🛒 Ver Mi Carrito de Compras",
                    "description": "Revisa tus productos agregados y total a pagar"
                }
            ]
        }
    ]

    body = (
        "🛠️ *Catálogo Interactivo Ferretería Castor* 🦫\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Selecciona un departamento para ver los productos, precios y stock en tiempo real directamente aquí:"
    )

    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Explorar Catálogo 📋",
        sections=sections,
        footer="Ferretería Castor • Compras en WhatsApp",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

CATEGORY_MAP = {
    "cat_herramientas_elec": "Herramientas Eléctricas",
    "cat_herramientas_man": "Herramientas Manuales",
    "cat_construccion": "Construcción",
    "cat_pinturas": "Pinturas",
    "cat_plomeria": "Plomería",
    "cat_electricidad": "Electricidad"
}

async def send_products_in_category(phone: str, cat_id: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra la lista interactiva de productos de una categoría específica."""
    category_name = CATEGORY_MAP.get(cat_id, "Herramientas Eléctricas")
    
    async with async_session() as session:
        stmt = select(Product).where(Product.category == category_name, Product.is_active == True).limit(10)
        res = await session.execute(stmt)
        products = res.scalars().all()

    if not products:
        msg = f"No encontramos productos disponibles en la categoría *{category_name}*."
        buttons = [
            {"id": "flow_catalogo", "title": "📋 Ver Categorías"},
            {"id": "menu_inicio",   "title": "🏠 Menú Principal"}
        ]
        await flows._send_buttons(phone, msg, buttons, internal_key=internal_key, phone_number_id=phone_number_id)
        return

    rows = []
    for p in products:
        stock_text = f"Stock: {p.stock}" if p.stock > 0 else "Agotado"
        desc = f"${float(p.price):.2f} • {stock_text}"
        rows.append({
            "id": f"prod_view_{p.sku}",
            "title": p.name[:24],  # WhatsApp limit 24 chars for row title
            "description": desc[:72]
        })

    sections = [
        {
            "title": f"Items en {category_name[:20]}",
            "rows": rows
        }
    ]

    body = (
        f"🏷️ *{category_name.upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Selecciona un producto para ver sus detalles y agregarlo a tu carrito:"
    )

    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Ver Productos 🔍",
        sections=sections,
        footer="Precios incluyen IVA",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_product_detail(phone: str, sku: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra la ficha técnica del producto con botones para agregarlo al carrito."""
    async with async_session() as session:
        stmt = select(Product).where(Product.sku == sku, Product.is_active == True)
        res = await session.execute(stmt)
        p = res.scalar_one_or_none()

    if not p:
        msg = "⚠️ El producto solicitado no está disponible."
        buttons = [{"id": "flow_catalogo", "title": "📋 Catálogo"}]
        await flows._send_buttons(phone, msg, buttons, internal_key=internal_key, phone_number_id=phone_number_id)
        return

    stock_centro = (p.sucursal_stocks or {}).get("Centro", 0)
    stock_norte = (p.sucursal_stocks or {}).get("Norte", 0)

    body = (
        f"🛠️ *{p.name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ *Precio:* *${float(p.price):.2f}* (IVA inc.)\n"
        f"📦 *Disponibilidad:* {p.stock} unidades en total\n"
        f"📍 *Stock Centro:* {stock_centro} | *Norte:* {stock_norte}\n"
        f"🔢 *Código:* `{p.sku}`\n\n"
        f"📝 *Detalles:*\n"
        f"{p.description or 'Herramienta de primera calidad con garantía.'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Deseas agregarlo a tu pedido?"
    )

    buttons = [
        {"id": f"cart_add_{p.sku}_1", "title": "➕ Agregar al Carrito"},
        {"id": "cart_view",          "title": "🛒 Ver Mi Carrito"},
        {"id": "flow_catalogo",       "title": "🔙 Más Productos"}
    ]

    await flows._send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Ferretería Castor • Compra Fácil",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def handle_add_to_cart(phone: str, sku: str, quantity: int, redis_client: Any, internal_key: str, phone_number_id: Optional[str] = None):
    """Agrega el producto al carrito del usuario y muestra mensaje de confirmación con botones rápidos."""
    result = await add_item_to_cart(redis_client, phone, sku, quantity)
    if not result:
        await flows._send(phone, "⚠️ No pudimos agregar el producto. Inténtalo de nuevo.", internal_key, phone_number_id)
        return

    prod = result["product"]
    cart = result["cart"]
    items_count = sum(it["quantity"] for it in cart.get("items", {}).values())
    total_price = sum(it["subtotal"] for it in cart.get("items", {}).values())

    body = (
        f"✅ *¡Producto Agregado al Carrito!* 🛒\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• *{prod.name}*\n"
        f"• Cantidad: {quantity} unid. (${float(prod.price * quantity):.2f})\n\n"
        f"🛍️ *Tu Carrito actual:* {items_count} artículo(s)\n"
        f"💰 *Total acumulado:* *${total_price:.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Qué deseas hacer ahora?"
    )

    buttons = [
        {"id": "cart_view",     "title": "🛒 Ver Mi Carrito"},
        {"id": "flow_catalogo", "title": "➕ Seguir Comprando"},
        {"id": "checkout_start","title": "✅ Pedir Ahora"}
    ]

    await flows._send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Ferretería Castor",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_cart_view(phone: str, redis_client: Any, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra el carrito de compras en el chat con opción de checkout o vaciar."""
    cart = await get_cart(redis_client, phone)
    items = list(cart.get("items", {}).values())

    if not items:
        body = (
            "🛒 *Tu Carrito de Compras está vacío.* 🦫\n\n"
            "Explora nuestro catálogo para seleccionar productos y armar tu pedido directamente aquí:"
        )
        buttons = [
            {"id": "flow_catalogo", "title": "📋 Ver Catálogo"},
            {"id": "menu_inicio",   "title": "🏠 Menú Principal"}
        ]
        await flows._send_buttons(phone, body, buttons, internal_key=internal_key, phone_number_id=phone_number_id)
        return

    lines = []
    subtotal = Decimal("0.00")
    for i, it in enumerate(items, 1):
        item_sub = Decimal(str(it["subtotal"]))
        subtotal += item_sub
        lines.append(f"{i}. *{it['quantity']}x {it['name']}* — ${item_sub:.2f}")

    items_text = "\n".join(lines)
    tax = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
    total = subtotal + tax

    body = (
        f"🛒 *TU CARRITO DE COMPRAS* 🦫\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{items_text}\n\n"
        f"💵 *Subtotal:* ${subtotal:.2f}\n"
        f"📊 *IVA (15%):* ${tax:.2f}\n"
        f"💰 *TOTAL A PAGAR:* *${total:.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Deseas confirmar tu pedido o agregar más productos?"
    )

    buttons = [
        {"id": "checkout_start", "title": "✅ Finalizar Pedido"},
        {"id": "flow_catalogo",  "title": "➕ Más Productos"},
        {"id": "cart_clear",     "title": "🗑️ Vaciar Carrito"}
    ]

    await flows._send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Ferretería Castor • Pedidos en WhatsApp",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def prompt_delivery_method(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Pregunta el tipo de entrega (Retiro en local o Envío a domicilio)."""
    body = (
        "🚚 *MÉTODO DE ENTREGA* 📍\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "¿Cómo prefieres recibir tu pedido de Ferretería Castor?"
    )
    buttons = [
        {"id": "order_pickup",   "title": "📍 Retiro en Sucursal"},
        {"id": "order_delivery", "title": "🛵 Envío a Domicilio"},
        {"id": "cart_view",      "title": "🔙 Ver Carrito"}
    ]
    await flows._send_buttons(phone, body, buttons, internal_key=internal_key, phone_number_id=phone_number_id)

async def prompt_sucursal_selection(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra la lista de sucursales para retiro en tienda."""
    sections = [
        {
            "title": "📍 Selecciona tu Sucursal",
            "rows": [
                {"id": "order_suc_centro",  "title": "📍 Sucursal Centro",  "description": "Matriz Centro • Av. Pichincha"},
                {"id": "order_suc_norte",   "title": "📍 Sucursal Norte",   "description": "Av. Eloy Alfaro N56-10"},
                {"id": "order_suc_sur",     "title": "📍 Sucursal Sur",     "description": "Av. Maldonado y Moraspungo"},
                {"id": "order_suc_cumbaya", "title": "📍 Sucursal Cumbayá", "description": "Av. Interoceánica km 11"}
            ]
        }
    ]
    body = "Elige la sucursal donde deseas retirar tus productos:"
    await flows._send_list(phone, body, "Elegir Sucursal 📍", sections, internal_key=internal_key, phone_number_id=phone_number_id)

async def prompt_payment_method(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra los métodos de pago disponibles."""
    body = (
        "💳 *FORMA DE PAGO* 💵\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Selecciona cómo realizarás el pago de tu pedido:"
    )
    buttons = [
        {"id": "pay_efectivo",      "title": "💵 Efectivo"},
        {"id": "pay_transferencia", "title": "🏦 Transferencia"},
        {"id": "pay_tarjeta",       "title": "💳 Tarjeta"}
    ]
    await flows._send_buttons(phone, body, buttons, internal_key=internal_key, phone_number_id=phone_number_id)

async def complete_in_chat_order(
    phone: str,
    redis_client: Any,
    db: AsyncSession,
    payment_method: str,
    internal_key: str,
    phone_number_id: Optional[str] = None
) -> Optional[str]:
    """Crea la orden en PostgreSQL, descuenta inventario, notifica a WhatsApp y Chatwoot."""
    cart = await get_cart(redis_client, phone)
    items_dict = cart.get("items", {})

    if not items_dict:
        await flows._send(phone, "⚠️ Tu carrito está vacío. Agrega productos antes de confirmar.", internal_key, phone_number_id)
        return None

    # 1. Validar productos y calcular totales
    subtotal = Decimal("0.00")
    order_items_to_save = []
    
    for sku, it in items_dict.items():
        stmt = select(Product).where(Product.sku == sku, Product.is_active == True)
        res = await db.execute(stmt)
        prod = res.scalar_one_or_none()
        
        if not prod:
            continue
            
        qty = it["quantity"]
        prod.stock = max(0, prod.stock - qty)
        
        sucursal = cart.get("sucursal", "Centro")
        if prod.sucursal_stocks and sucursal in prod.sucursal_stocks:
            prod.sucursal_stocks[sucursal] = max(0, prod.sucursal_stocks[sucursal] - qty)
        db.add(prod)
        
        item_sub = Decimal(str(prod.price)) * Decimal(qty)
        subtotal += item_sub
        order_items_to_save.append({
            "product_id": prod.id,
            "product_name": prod.name,
            "sku": prod.sku,
            "unit_price": Decimal(str(prod.price)),
            "quantity": qty,
            "subtotal": item_sub
        })

    tax = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
    total = subtotal + tax

    # 2. Generar número de orden
    clean_phone = phone.replace("+", "").replace(" ", "").strip()
    order_number = f"CAST-{datetime.utcnow().year}-{random.randint(1000, 9999)}"
    
    session_service = SessionService(db, redis_client)
    phone_hash = session_service.derive_phone_hash(clean_phone)

    customer_name = cart.get("customer_name") or "Cliente WhatsApp"
    delivery_type = cart.get("delivery_type") or "pickup"
    delivery_address = cart.get("address")
    sucursal = cart.get("sucursal") or "Centro"

    # 3. Guardar orden
    order = Order(
        order_number=order_number,
        phone_hash=phone_hash,
        customer_phone=clean_phone,
        customer_name=customer_name,
        delivery_type=delivery_type,
        delivery_address=delivery_address,
        sucursal=sucursal,
        status="created",
        payment_method=payment_method,
        subtotal=subtotal,
        tax=tax,
        total=total
    )
    db.add(order)
    await db.flush()

    for oi_data in order_items_to_save:
        oi = OrderItem(
            order_id=order.id,
            product_id=oi_data["product_id"],
            product_name=oi_data["product_name"],
            sku=oi_data["sku"],
            unit_price=oi_data["unit_price"],
            quantity=oi_data["quantity"],
            subtotal=oi_data["subtotal"]
        )
        db.add(oi)

    await db.commit()

    # 4. Vaciar carrito
    await clear_cart(redis_client, phone)

    # 5. Enviar mensaje de confirmación con recibo en el chat
    items_summary_lines = [f"• {it['quantity']}x *{it['product_name']}* (${it['subtotal']:.2f})" for it in order_items_to_save]
    items_text = "\n".join(items_summary_lines)

    delivery_info = f"📍 *Retiro en Sucursal:* {sucursal}" if delivery_type == "pickup" else f"🚚 *Envío a Domicilio:* {delivery_address}"

    receipt_msg = (
        f"🎉 *¡PEDIDO CONFIRMADO CON ÉXITO!* 🦫\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *N° de Pedido:* `{order_number}`\n"
        f"{delivery_info}\n"
        f"💳 *Método de Pago:* {payment_method.capitalize()}\n\n"
        f"📦 *Productos Solicitados:*\n"
        f"{items_text}\n\n"
        f"💵 *Subtotal:* ${subtotal:.2f}\n"
        f"📊 *IVA (15%):* ${tax:.2f}\n"
        f"💰 *TOTAL:* *${total:.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *Estado actual:* ⏳ *Preparando en Bodega (Picking)*\n\n"
        f"¡Gracias por tu compra en Ferretería Castor! Te notificaremos cuando tu pedido esté listo."
    )

    buttons = [
        {"id": "flow_pedido",  "title": "📦 Consultar Estado"},
        {"id": "flow_asesor",  "title": "👨‍💼 Hablar con Asesor"},
        {"id": "menu_inicio",  "title": "🏠 Menú Principal"}
    ]

    await flows._send_buttons(
        phone=phone,
        body=receipt_msg,
        buttons=buttons,
        footer="Ferretería Castor • Atención 24/7",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

    # 6. Notificar en Chatwoot
    try:
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            contact_id = await chatwoot.get_or_create_contact(clean_phone, f"Cliente {customer_name}")
            if contact_id:
                conv_id = await chatwoot.get_or_create_conversation(contact_id)
                if conv_id:
                    note = (
                        f"🛍️ *NUEVO PEDIDO NATIVO EN WHATSAPP* 🛒\n\n"
                        f"• *Pedido:* {order_number}\n"
                        f"• *Cliente:* +{clean_phone}\n"
                        f"• *Entrega:* {delivery_type.upper()} ({sucursal or delivery_address})\n"
                        f"• *Pago:* {payment_method.capitalize()}\n"
                        f"• *Total:* ${total:.2f}\n\n"
                        f"📦 *Items:*\n{items_text}"
                    )
                    await chatwoot.post_message(conv_id, note, is_private=True)
    except Exception as cw_err:
        logger.error(f"Error sincronizando orden nativa con Chatwoot: {cw_err}")

    return order_number
