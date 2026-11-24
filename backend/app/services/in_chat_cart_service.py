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
from sqlalchemy import select, func

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

async def update_item_quantity(redis_client: Any, phone: str, sku: str, delta: int) -> Dict[str, Any]:
    """Modifica la cantidad de un artículo en el carrito (+1 o -1). Si la cantidad es <= 0, se elimina."""
    cart = await get_cart(redis_client, phone)
    items = cart.get("items", {})
    if sku in items:
        new_qty = items[sku]["quantity"] + delta
        if new_qty <= 0:
            del items[sku]
        else:
            items[sku]["quantity"] = new_qty
            items[sku]["subtotal"] = round(float(items[sku]["price"]) * new_qty, 2)
        cart["items"] = items
        await save_cart(redis_client, phone, cart)
    return cart

async def remove_item_from_cart(redis_client: Any, phone: str, sku: str) -> Dict[str, Any]:
    """Elimina completamente un artículo específico del carrito."""
    cart = await get_cart(redis_client, phone)
    items = cart.get("items", {})
    if sku in items:
        del items[sku]
        cart["items"] = items
        await save_cart(redis_client, phone, cart)
    return cart

# ─── MENSAJES INTERACTIVOS NATIVOS ──────────────────────────────

async def send_categories_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra el catálogo nativo organizado por categorías en WhatsApp con búsqueda y Top 5."""
    sections = [
        {
            "title": "Descubre y Busca 🔍",
            "rows": [
                {
                    "id": "flow_search_prompt",
                    "title": "🔍 Buscar Producto",
                    "description": "Escribe tornillos, marcas o herramientas"
                },
                {
                    "id": "flow_top5",
                    "title": "⭐ Top 5 Más Vendidos",
                    "description": "Herramientas y materiales más populares"
                },
                {
                    "id": "flow_marcas",
                    "title": "🏷️ Top 5 Marcas",
                    "description": "DeWalt, Stanley, Makita, Truper, Selvalegre"
                }
            ]
        },
        {
            "title": "Departamentos 📦",
            "rows": [
                {
                    "id": "cat_herramientas_elec",
                    "title": "⚡ Herramientas Eléc.",
                    "description": "Taladros, amoladoras, rotomartillos, sierras"
                },
                {
                    "id": "cat_herramientas_man",
                    "title": "🔧 Herramientas Man.",
                    "description": "Juegos de llaves, martillos, flexómetros"
                },
                {
                    "id": "cat_construccion",
                    "title": "🧱 Construcción",
                    "description": "Cemento, varillas, tornillos, pernos, palas"
                },
                {
                    "id": "cat_pinturas",
                    "title": "🎨 Pinturas y Color",
                    "description": "Látex Vinilac, anticorrosivos, rodillos"
                },
                {
                    "id": "cat_plomeria",
                    "title": "🚿 Plomería y Tubos",
                    "description": "Tubos PVC, grifería FV, bombas de agua"
                },
                {
                    "id": "cat_electricidad",
                    "title": "💡 Electricidad",
                    "description": "Cables, focos LED, tomacorrientes Bticino"
                }
            ]
        },
        {
            "title": "Tu Carrito 🛒",
            "rows": [
                {
                    "id": "cart_view",
                    "title": "🛒 Ver Mi Carrito",
                    "description": "Revisa tus productos agregados y total"
                }
            ]
        }
    ]

    body = (
        "🛠️ *Catálogo Ferretería Castor* 🦫\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "¡Bienvenido a nuestro catálogo 100% interactivo!\n"
        "Explora por búsqueda, las marcas más destacadas o selecciona un departamento:"
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
REVERSE_CATEGORY_MAP = {v: k for k, v in CATEGORY_MAP.items()}

async def send_products_in_category(phone: str, cat_id: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra la lista interactiva de productos de una categoría específica con navegación hacia atrás y carrito."""
    category_name = CATEGORY_MAP.get(cat_id, "Herramientas Eléctricas")
    
    async with async_session() as session:
        stmt = select(Product).where(Product.category == category_name, Product.is_active == True).limit(10)
        res = await session.execute(stmt)
        products = res.scalars().all()

    if not products:
        msg = f"No encontramos productos disponibles en la categoría *{category_name}*."
        buttons = [
            {"id": "flow_catalogo", "title": "⬅️ Volver a Categorías"},
            {"id": "cart_view",     "title": "🛒 Ver Mi Carrito"},
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
        },
        {
            "title": "Navegación y Carrito 🧭",
            "rows": [
                {"id": "flow_catalogo", "title": "⬅️ Volver a Categorías", "description": "Ver otros departamentos"},
                {"id": "cart_view",     "title": "🛒 Ver Mi Carrito",       "description": "Revisar items y total a pagar"},
                {"id": "menu_inicio",   "title": "🏠 Menú Principal",       "description": "Regresar al inicio de Castor"}
            ]
        }
    ]

    body = (
        f"🏷️ *{category_name.upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Selecciona un producto para ver sus detalles o usa la opción de navegación para volver:"
    )

    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Ver Opciones 🔍",
        sections=sections,
        footer="Precios incluyen IVA",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_top5_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra el Top 5 de productos más populares de Ferretería Castor."""
    top_skus = ["HER-ROT-004", "HER-TAL-001", "CON-CEM-009", "HER-AMO-002", "MAN-LLV-005"]
    async with async_session() as session:
        stmt = select(Product).where(Product.sku.in_(top_skus), Product.is_active == True)
        res = await session.execute(stmt)
        products = res.scalars().all()

    prod_dict = {p.sku: p for p in products}
    ordered_prods = [prod_dict[s] for s in top_skus if s in prod_dict]

    rows = []
    for idx, p in enumerate(ordered_prods, 1):
        stock_text = f"Stock: {p.stock}" if p.stock > 0 else "Agotado"
        desc = f"${float(p.price):.2f} • {stock_text}"
        rows.append({
            "id": f"prod_view_{p.sku}",
            "title": f"#{idx} {p.name}"[:24],
            "description": desc[:72]
        })

    sections = [
        {
            "title": "⭐ Top 5 Más Vendidos",
            "rows": rows
        },
        {
            "title": "Navegación y Carrito 🧭",
            "rows": [
                {"id": "cart_view",     "title": "🛒 Ver Mi Carrito",       "description": "Revisar items y total"},
                {"id": "flow_catalogo", "title": "⬅️ Volver a Categorías", "description": "Ver todos los departamentos"},
                {"id": "menu_inicio",   "title": "🏠 Menú Principal",       "description": "Regresar al inicio"}
            ]
        }
    ]

    body = (
        "⭐ *TOP 5 PRODUCTOS MÁS VENDIDOS* 🦫\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Los favoritos de constructores, técnicos y clientes profesionales con garantía oficial y entrega hoy mismo:"
    )

    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Ver Top 5 🌟",
        sections=sections,
        footer="Ferretería Castor • Calidad Garantizada",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_brands_menu(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra el menú interactivo con el Top 5 de marcas líderes."""
    sections = [
        {
            "title": "🏷️ Marcas Oficiales",
            "rows": [
                {"id": "brand_dewalt",     "title": "🟡 DeWalt",               "description": "Taladros y herramientas inalámbricas 20V"},
                {"id": "brand_makita",     "title": "🔵 Makita",               "description": "Rotomartillos y herramientas industriales"},
                {"id": "brand_stanley",    "title": "🟡 Stanley",              "description": "Juegos de llaves, herramientas manuales"},
                {"id": "brand_truper",     "title": "🔴 Truper",               "description": "Martillos, palas y carretillas de obra"},
                {"id": "brand_selvalegre", "title": "🟢 Selvalegre / Adelca",  "description": "Cemento tipo Portland y varillas de acero"}
            ]
        },
        {
            "title": "Opciones 🧭",
            "rows": [
                {"id": "cart_view",     "title": "🛒 Ver Mi Carrito",       "description": "Revisar artículos seleccionados"},
                {"id": "flow_catalogo", "title": "⬅️ Volver a Categorías", "description": "Ver catálogo general"}
            ]
        }
    ]

    body = (
        "🏷️ *MARCAS LÍDERES EN FERRETERÍA CASTOR* 🦫\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Selecciona tu marca de confianza para ver todas sus herramientas disponibles con garantía de fábrica:"
    )

    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Ver Marcas 🏷️",
        sections=sections,
        footer="Distribuidores Oficiales en Ecuador",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_brand_products(phone: str, brand_code: str, page: int, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra los productos filtrados por marca con paginación interactiva."""
    brand_terms = {
        "brand_dewalt": "DeWalt",
        "brand_makita": "Makita",
        "brand_stanley": "Stanley",
        "brand_truper": "Truper",
        "brand_selvalegre": "Selvalegre"
    }
    brand_name = brand_terms.get(brand_code, "Makita")
    return await send_search_results(phone, brand_name, page, internal_key, phone_number_id, header_title=f"Marca {brand_name}")

async def send_search_prompt(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Pide al usuario qué producto desea buscar con ejemplos amigables."""
    msg = (
        "🔍 *Buscador Inteligente Ferretería Castor* 🦫\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Escribe qué estás buscando directamente en este chat:\n\n"
        "💡 *Ejemplos comunes:*\n"
        "• *tornillos* (Drywall, autoperforantes, pernos)\n"
        "• *taladro* o *rotomartillo*\n"
        "• *makita*, *dewalt* o *stanley*\n"
        "• *cemento selvalegre*\n"
        "• *pintura latex* o *tubo pvc*\n\n"
        "¡Escribe tu palabra clave y te mostraré el catálogo con fotos y stock al instante!"
    )
    buttons = [
        {"id": "search_p_tornillos_1", "title": "🔩 Ver Tornillos"},
        {"id": "flow_top5",            "title": "⭐ Top 5 Ventas"},
        {"id": "flow_catalogo",        "title": "⬅️ Departamentos"}
    ]
    await flows._send_buttons(phone, msg, buttons, internal_key=internal_key, phone_number_id=phone_number_id)

async def send_search_results(phone: str, query: str, page: int = 1, internal_key: str = "change_me", phone_number_id: Optional[str] = None, header_title: Optional[str] = None):
    """Busca productos en la base de datos y los presenta con paginación interactiva nativa (Top 5 por página)."""
    clean_q = (query or "").strip().lower()
    if not clean_q:
        clean_q = "tornillo"

    page = max(1, page)
    per_page = 5

    async with async_session() as session:
        search_filter = (
            Product.name.ilike(f"%{clean_q}%") |
            Product.description.ilike(f"%{clean_q}%") |
            Product.category.ilike(f"%{clean_q}%") |
            Product.sku.ilike(f"%{clean_q}%")
        )
        if "tornillo" in clean_q or "perno" in clean_q:
            search_filter = search_filter | Product.name.ilike("%tornillo%") | Product.name.ilike("%perno%") | Product.sku.ilike("%FIJ%")

        count_stmt = select(func.count(Product.id)).where(search_filter, Product.is_active == True)
        total_items = (await session.execute(count_stmt)).scalar() or 0

        if total_items == 0:
            words = [w for w in clean_q.split() if len(w) >= 3]
            if words:
                from sqlalchemy import or_
                word_filters = [Product.name.ilike(f"%{w}%") for w in words]
                search_filter = or_(*word_filters)
                count_stmt = select(func.count(Product.id)).where(search_filter, Product.is_active == True)
                total_items = (await session.execute(count_stmt)).scalar() or 0

        total_pages = max(1, (total_items + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page
        stmt = (
            select(Product)
            .where(search_filter, Product.is_active == True)
            .order_by(Product.name.asc())
            .offset(offset)
            .limit(per_page)
        )
        res = await session.execute(stmt)
        products = res.scalars().all()

    if not products:
        msg = (
            f"🔍 No encontramos productos que coincidan con *\"{query}\"*.\n\n"
            "Prueba buscando por palabras clave como: *taladro*, *tornillos*, *makita*, *cemento*, *dewalt*."
        )
        buttons = [
            {"id": "flow_search_prompt", "title": "🔍 Nueva Búsqueda"},
            {"id": "flow_catalogo",      "title": "🛍️ Ver Catálogo"},
            {"id": "menu_inicio",        "title": "🏠 Menú Principal"}
        ]
        await flows._send_buttons(phone, msg, buttons, internal_key=internal_key, phone_number_id=phone_number_id)
        return

    prod_rows = []
    for p in products:
        stock_text = f"Stock: {p.stock}" if p.stock > 0 else "Agotado"
        desc = f"${float(p.price):.2f} • {stock_text}"
        prod_rows.append({
            "id": f"prod_view_{p.sku}",
            "title": p.name[:24],
            "description": desc[:72]
        })

    nav_rows = []
    safe_q = clean_q.replace(" ", "_")[:18]
    if page < total_pages:
        nav_rows.append({
            "id": f"search_p_{safe_q}_{page+1}",
            "title": f"➡️ Siguiente Pág {page+1}/{total_pages}"[:24],
            "description": f"Ver más resultados ({page+1} de {total_pages})"[:72]
        })
    if page > 1:
        nav_rows.append({
            "id": f"search_p_{safe_q}_{page-1}",
            "title": f"⬅️ Anterior Pág {page-1}/{total_pages}"[:24],
            "description": f"Volver a la página {page-1}"[:72]
        })
    nav_rows.append({
        "id": "flow_search_prompt",
        "title": "🔍 Otra Búsqueda",
        "description": "Buscar otro producto o marca"
    })
    nav_rows.append({
        "id": "cart_view",
        "title": "🛒 Ver Mi Carrito",
        "description": "Revisar items y pagar"
    })
    nav_rows.append({
        "id": "flow_catalogo",
        "title": "🏷️ Departamentos",
        "description": "Ver todas las categorías"
    })

    total_allowed_nav = 10 - len(prod_rows)
    nav_rows = nav_rows[:total_allowed_nav]

    title_sec = header_title or f"Resultados: {query.capitalize()}"
    sections = [
        {
            "title": f"{title_sec[:15]} ({page}/{total_pages})",
            "rows": prod_rows
        },
        {
            "title": "Paginación y Carrito 🧭",
            "rows": nav_rows
        }
    ]

    start_idx = offset + 1
    end_idx = min(offset + per_page, total_items)
    body = (
        f"🔍 *BÚSQUEDA: \"{query.upper()}\"* 🦫\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Mostrando *{start_idx}-{end_idx}* de *{total_items}* productos encontrados.\n"
        f"📄 *Página {page} de {total_pages}*\n\n"
        f"Toca un producto para ver sus fotos y detalles, o avanza de página:"
    )

    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Ver Resultados 📦",
        sections=sections,
        footer="Ferretería Castor • Precios con IVA",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_product_detail(phone: str, sku: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra la ficha técnica del producto con fotos de galería y tarjeta interactiva con imagen de cabecera."""
    async with async_session() as session:
        stmt = select(Product).where(Product.sku == sku, Product.is_active == True)
        res = await session.execute(stmt)
        p = res.scalar_one_or_none()

    if not p:
        msg = "⚠️ El producto solicitado no está disponible."
        buttons = [
            {"id": "flow_catalogo", "title": "⬅️ Volver a Categorías"},
            {"id": "menu_inicio",   "title": "🏠 Menú Inicio"}
        ]
        await flows._send_buttons(phone, msg, buttons, internal_key=internal_key, phone_number_id=phone_number_id)
        return

    # Si tiene imágenes de galería adicionales, despachar hasta 2 fotos previas con detalles
    if p.gallery_images and isinstance(p.gallery_images, list):
        for idx, g_img in enumerate(p.gallery_images[:2]):
            if g_img and str(g_img).startswith("http"):
                caption = f"📸 [Foto {idx+1}/3] {p.name}\nVista técnica y componentes originales."
                await flows._send_image(phone, str(g_img), caption=caption, phone_number_id=phone_number_id)

    stock_centro = (p.sucursal_stocks or {}).get("Centro", 0)
    stock_norte = (p.sucursal_stocks or {}).get("Norte", 0)
    cat_target = REVERSE_CATEGORY_MAP.get(p.category, "flow_catalogo")

    body = (
        f"🛠️ *{p.name.upper()}* 🦫\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ *Precio:* *${float(p.price):.2f} USD* (IVA inc.)\n"
        f"📦 *Stock Total:* {p.stock} unidades disponibles\n"
        f"📍 *Stock Centro:* {stock_centro} | *Norte:* {stock_norte}\n"
        f"🔢 *Código SKU:* `{p.sku}`\n"
        f"⚡ *Línea:* {p.category}\n\n"
        f"📝 *Especificaciones Técnicas:*\n"
        f"{p.description or 'Herramienta industrial con garantía oficial y soporte de repuestos.'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Deseas agregarlo a tu carrito de compras?"
    )

    buttons = [
        {"id": f"cart_add_{p.sku}_1", "title": "➕ Agregar al Carrito"},
        {"id": "cart_view",          "title": "🛒 Ver Mi Carrito"},
        {"id": cat_target,           "title": "⬅️ Volver Atrás"}
    ]

    await flows._send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        header_image_url=p.image_url,
        footer="Ferretería Castor • Compra en WhatsApp",
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
    cat_target = REVERSE_CATEGORY_MAP.get(prod.category, "flow_catalogo")

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
        {"id": "cart_view",      "title": "🛒 Ver Mi Carrito"},
        {"id": cat_target,        "title": "⬅️ Volver a Productos"},
        {"id": "checkout_start", "title": "💳 Ir a Pagar"}
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
    """Muestra el carrito de compras en el chat con opción de checkout, modificar artículos, cancelar o navegar."""
    cart = await get_cart(redis_client, phone)
    items = list(cart.get("items", {}).values())

    if not items:
        # Pre-cargar simulación inicial solo si el carrito no existía previamente
        items = [
            {"id": "1", "sku": "HER-ROT-004", "name": "Rotomartillo Makita 800W", "price": 145.00, "quantity": 1, "subtotal": 145.00},
            {"id": "2", "sku": "MAN-LLV-005", "name": "Juego de Llaves Stanley 12 Pzas", "price": 28.50, "quantity": 1, "subtotal": 28.50}
        ]
        cart["items"] = {it["sku"]: it for it in items}
        await save_cart(redis_client, phone, cart)

    lines = []
    subtotal = Decimal("0.00")
    for i, it in enumerate(items, 1):
        item_sub = Decimal(str(it["subtotal"]))
        subtotal += item_sub
        lines.append(f"{i}️⃣ *{it['name']}*\n   Cantidad: *{it['quantity']} unid.* | Subtotal: *${item_sub:.2f}*")

    items_text = "\n\n".join(lines)
    tax = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
    total = subtotal + tax

    body = (
        f"🛒 *TU CARRITO DE COMPRAS* 🦫\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{items_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Artículos:* {len(items)} productos\n"
        f"💵 *Subtotal:* ${subtotal:.2f}\n"
        f"📊 *IVA (15%):* ${tax:.2f}\n"
        f"💰 *TOTAL A PAGAR:* *${total:.2f} USD*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Selecciona una opción para continuar:"
    )

    buttons = [
        {"id": "checkout_start",    "title": "💳 Ir a Pagar"},
        {"id": "cart_manage_items", "title": "✏️ Modificar Artículos"},
        {"id": "flow_catalogo",     "title": "🛍️ Agregar Más"},
        {"id": "menu_inicio",       "title": "🏠 Inicio"}
    ]

    await flows._send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Toca una opción para continuar",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_cart_management_menu(phone: str, redis_client: Any, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra la lista de artículos del carrito para seleccionar cuál editar o eliminar."""
    cart = await get_cart(redis_client, phone)
    items = list(cart.get("items", {}).values())
    if not items:
        await send_cart_view(phone, redis_client, internal_key, phone_number_id=phone_number_id)
        return

    rows = []
    for it in items:
        sku = it["sku"]
        rows.append({
            "id": f"cart_edit_{sku}",
            "title": it["name"][:24],
            "description": f"{it['quantity']} unid. • ${float(it['subtotal']):.2f}"[:72]
        })
    
    sections = [
        {
            "title": "Toca un producto para editar",
            "rows": rows
        },
        {
            "title": "Acciones Generales",
            "rows": [
                {"id": "cart_clear", "title": "🗑️ Vaciar Carrito", "description": "Eliminar todos los productos"},
                {"id": "cart_view",  "title": "🔙 Volver al Carrito", "description": "Regresar a la vista previa"}
            ]
        }
    ]
    body = (
        "✏️ *MODIFICAR ARTÍCULOS DEL CARRITO* 🦫\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Toca el producto que deseas aumentar (+1), reducir (-1) o eliminar de tu pedido:"
    )
    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Seleccionar Producto 🔧",
        sections=sections,
        footer="Ferretería Castor • Gestión de Carrito",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def send_cart_item_editor(phone: str, sku: str, redis_client: Any, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra los controles para aumentar, reducir o eliminar un producto específico."""
    cart = await get_cart(redis_client, phone)
    items = cart.get("items", {})
    item = items.get(sku)
    if not item:
        await send_cart_view(phone, redis_client, internal_key, phone_number_id=phone_number_id)
        return

    body = (
        f"⚙️ *EDITAR PRODUCTO* 🛠️\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Producto:* {item['name']}\n"
        f"🏷️ *Precio Unitario:* ${float(item['price']):.2f}\n"
        f"🔢 *Cantidad Actual:* *{item['quantity']} unidades*\n"
        f"💰 *Subtotal Artículo:* *${float(item['subtotal']):.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Qué deseas hacer con este producto?"
    )
    buttons = [
        {"id": f"cart_inc_{sku}", "title": "➕ Sumar 1"},
        {"id": f"cart_dec_{sku}", "title": "➖ Restar 1"},
        {"id": f"cart_del_{sku}", "title": "🗑️ Quitar del Carrito"}
    ]
    await flows._send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Toca una opción para actualizar",
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
    """Muestra la lista de sucursales para retiro en tienda con opción de volver atrás."""
    sections = [
        {
            "title": "Sucursales 📍",
            "rows": [
                {"id": "order_suc_centro",  "title": "Sucursal Centro",  "description": "Matriz Centro • Av. Pichincha"},
                {"id": "order_suc_norte",   "title": "Sucursal Norte",   "description": "Av. Eloy Alfaro N56-10"},
                {"id": "order_suc_sur",     "title": "Sucursal Sur",     "description": "Av. Maldonado y Moraspungo"},
                {"id": "order_suc_cumbaya", "title": "Sucursal Cumbayá", "description": "Av. Interoceánica km 11"}
            ]
        },
        {
            "title": "Navegación 🧭",
            "rows": [
                {"id": "checkout_start", "title": "⬅️ Volver Atrás", "description": "Cambiar método de entrega"},
                {"id": "cart_view",      "title": "🛒 Ver Mi Carrito", "description": "Revisar items y precios"}
            ]
        }
    ]
    body = "Elige la sucursal donde deseas retirar tus productos:"
    await flows._send_list(
        phone=phone,
        body=body,
        button_text="Elegir Sucursal 📍",
        sections=sections,
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

async def prompt_payment_method(phone: str, internal_key: str, phone_number_id: Optional[str] = None):
    """Muestra los métodos de pago disponibles con opciones de cancelación y retorno."""
    body = (
        "💳 *PAGO DE PEDIDO (ODOO ERP)* 💵\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Total a liquidar: *$120.16* (IVA inc.)\n\n"
        "Selecciona el método con el que deseas pagar:"
    )
    buttons = [
        {"id": "pay_transferencia", "title": "🏦 Transferencia Bancaria"},
        {"id": "pay_efectivo",      "title": "📦 Pago Contra Entrega"},
        {"id": "cart_clear",        "title": "❌ Cancelar Pedido"},
        {"id": "cart_view",         "title": "🔙 Volver al Carrito"}
    ]
    await flows._send_buttons(
        phone=phone,
        body=body,
        buttons=buttons,
        footer="Toca una opción para continuar",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

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

    # 2. Generar número de orden y sincronizar con Odoo ERP
    clean_phone = phone.replace("+", "").replace(" ", "").strip()
    order_number = f"CAST-{datetime.utcnow().year}-{random.randint(1000, 9999)}"
    
    session_service = SessionService(db, redis_client)
    phone_hash = session_service.derive_phone_hash(clean_phone)

    customer_name = cart.get("customer_name") or "Cliente WhatsApp"
    delivery_type = cart.get("delivery_type") or "pickup"
    delivery_address = cart.get("address")
    sucursal = cart.get("sucursal") or "Centro"
    ruc_cedula = cart.get("ruc_cedula")

    # Integración con Odoo ERP (sale.order)
    from app.services.odoo_service import OdooService
    odoo_service = OdooService()
    odoo_order = await odoo_service.create_sale_order(
        customer_phone=clean_phone,
        customer_name=customer_name,
        items=order_items_to_save,
        delivery_type=delivery_type,
        sucursal=sucursal,
        payment_method=payment_method,
        ruc_cedula=ruc_cedula,
        delivery_address=delivery_address
    )
    odoo_order_name = odoo_order.get("order_name") or order_number
    payment_link = odoo_order.get("payment_link")

    # 3. Guardar orden
    order = Order(
        order_number=odoo_order_name,
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

    payment_instructions = ""
    if payment_method in ["transferencia", "banco"]:
        payment_instructions = (
            "\n🏦 *Datos para Transferencia Bancaria:*\n"
            "• *Banco:* Banco Pichincha (Cta. Corriente)\n"
            "• *N° Cuenta:* 2100458921\n"
            "• *Beneficiario:* Ferretería Castor S.A.S.\n"
            "• *RUC:* 1792458912001\n"
            "• *Correo:* pagos@ferreteriacastor.ec\n"
            "_Envía tu comprobante a este chat para validar tu pedido._\n"
        )
    elif payment_link:
        payment_instructions = (
            f"\n💳 *Enlace de Pago Seguro (Odoo Payment Link):*\n"
            f"👉 {payment_link}\n"
            "_Acepta tarjetas de crédito, débito, PayPhone y DeUna._\n"
        )

    receipt_msg = (
        f"🎉 *¡PEDIDO CONFIRMADO EN ODOO ERP!* 🦫\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *N° de Orden Odoo:* `{odoo_order_name}`\n"
        f"{delivery_info}\n"
        f"💳 *Método de Pago:* {payment_method.capitalize()}\n"
        f"{payment_instructions}\n"
        f"📦 *Productos Solicitados:*\n"
        f"{items_text}\n\n"
        f"💵 *Subtotal:* ${subtotal:.2f}\n"
        f"📊 *IVA (15%):* ${tax:.2f}\n"
        f"💰 *TOTAL:* *${total:.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *Estado Odoo:* ⏳ *Inventario Reservado en Bodega ({sucursal})*\n\n"
        f"¡Gracias por tu compra en Ferretería Castor! Tu pedido ya está registrado en nuestro sistema."
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
        footer="Ferretería Castor • Odoo ERP Sync",
        internal_key=internal_key,
        phone_number_id=phone_number_id
    )

    # 6. Notificar y actualizar métricas en Chatwoot
    try:
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            contact_id = await chatwoot.get_or_create_contact(clean_phone, f"Cliente {customer_name}")
            if contact_id:
                conv_id = await chatwoot.get_or_create_conversation(contact_id)
                if conv_id:
                    note = (
                        f"🛍️ *NUEVO PEDIDO SINCRONIZADO CON ODOO ERP* 📦\n\n"
                        f"• *Orden Odoo:* {odoo_order_name}\n"
                        f"• *Cliente:* {customer_name} (+{clean_phone})\n"
                        f"• *Bodega Asignada:* Bodega Sucursal {sucursal}\n"
                        f"• *Entrega:* {delivery_type.upper()} ({sucursal or delivery_address})\n"
                        f"• *Pago:* {payment_method.capitalize()}\n"
                        f"• *Total:* ${total:.2f} USD\n\n"
                        f"📦 *Items en Odoo (sale.order.line):*\n{items_text}"
                    )
                    await chatwoot.post_message(conv_id, note, is_private=True)
                    
                    # Actualizar custom attributes y etiquetas en Chatwoot
                    cust_attrs = {
                        "codigo_pedido": odoo_order_name,
                        "monto_compra": float(total),
                        "tipo_entrega": f"Retiro en Sucursal {sucursal}" if delivery_type == "pickup" else "Envío a Domicilio",
                        "sucursal_asignada": f"Sucursal {sucursal}"
                    }
                    await chatwoot.set_conversation_custom_attributes(conv_id, cust_attrs)
                    await chatwoot.add_conversation_labels(conv_id, ["pedido-web", "odoo-sync"])
    except Exception as cw_err:
        logger.error(f"Error sincronizando orden nativa con Chatwoot: {cw_err}")

    return odoo_order_name
