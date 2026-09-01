import uuid
import logging
import random
import os
import json
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import httpx

from app.db.session import get_db_session
from app.db.tables import Product, Order, OrderItem, Conversation
from app.dependencies import get_redis
from app.services.session_service import SessionService
from app.services.chatwoot_service import ChatwootService
from app.config import settings

logger = logging.getLogger("chatbot-api.api.catalog")
router = APIRouter()

# ─── Pydantic Schemas ──────────────────────────────────────────

class OrderItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)

class CreateOrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    customer_phone: str = Field(..., min_length=8)
    delivery_type: str = Field("pickup", pattern="^(pickup|delivery)$")
    delivery_address: Optional[str] = None
    sucursal: Optional[str] = "Centro"
    payment_method: str = Field("efectivo", pattern="^(efectivo|transferencia|tarjeta)$")
    notes: Optional[str] = None
    items: List[OrderItemRequest] = Field(..., min_length=1)

# ─── REST Endpoints ────────────────────────────────────────────

@router.get("/api/catalog/categories")
async def get_categories(db: AsyncSession = Depends(get_db_session)):
    """Obtiene la lista de categorías con la cantidad de productos activos."""
    try:
        stmt = (
            select(Product.category, func.count(Product.id))
            .where(Product.is_active == True)
            .group_by(Product.category)
            .order_by(Product.category)
        )
        res = await db.execute(stmt)
        categories = [{"name": row[0], "count": row[1]} for row in res.all()]
        return {"success": True, "data": categories}
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al consultar categorías"})

@router.get("/api/catalog/products")
async def list_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    sucursal: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Lista los productos del catálogo con filtros de búsqueda y disponibilidad."""
    try:
        stmt = select(Product).where(Product.is_active == True)
        
        if category and category.lower() != "todos":
            stmt = stmt.where(Product.category == category)
            
        if q and q.strip():
            term = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Product.name).like(term),
                    func.lower(Product.description).like(term),
                    func.lower(Product.sku).like(term),
                    func.lower(Product.category).like(term)
                )
            )
            
        stmt = stmt.order_by(Product.category, Product.name)
        res = await db.execute(stmt)
        products = res.scalars().all()
        
        data = []
        for p in products:
            item = {
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "price": float(p.price),
                "stock": p.stock,
                "sucursal_stocks": p.sucursal_stocks or {},
                "image_url": p.image_url or "https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=600&auto=format&fit=crop&q=80",
                "in_stock": p.stock > 0
            }
            if sucursal and p.sucursal_stocks:
                item["sucursal_stock"] = p.sucursal_stocks.get(sucursal, 0)
            data.append(item)
            
        return {"success": True, "count": len(data), "data": data}
    except Exception as e:
        logger.error(f"Error listing catalog products: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al consultar productos"})

@router.get("/api/catalog/products/{product_id}")
async def get_product(product_id: str, db: AsyncSession = Depends(get_db_session)):
    """Obtiene los detalles de un producto por su ID."""
    try:
        p_uuid = uuid.UUID(product_id)
        stmt = select(Product).where(Product.id == p_uuid, Product.is_active == True)
        res = await db.execute(stmt)
        p = res.scalar_one_or_none()
        if not p:
            return JSONResponse(status_code=404, content={"success": False, "message": "Producto no encontrado"})
        return {
            "success": True,
            "data": {
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "price": float(p.price),
                "stock": p.stock,
                "sucursal_stocks": p.sucursal_stocks or {},
                "image_url": p.image_url,
                "in_stock": p.stock > 0
            }
        }
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al consultar el producto"})

@router.post("/api/catalog/orders")
async def create_order(
    order_req: CreateOrderRequest,
    db: AsyncSession = Depends(get_db_session),
    redis_client = Depends(get_redis)
):
    """Procesa el carrito de compras, descuenta stock y registra la orden con notificación a WhatsApp y Chatwoot."""
    try:
        # 1. Validar productos y calcular totales
        prod_ids = [uuid.UUID(item.product_id) for item in order_req.items]
        stmt = select(Product).where(Product.id.in_(prod_ids), Product.is_active == True)
        res = await db.execute(stmt)
        products_map = {str(p.id): p for p in res.scalars().all()}
        
        if len(products_map) != len(order_req.items):
            return JSONResponse(status_code=400, content={"success": False, "message": "Uno o más productos no están disponibles."})
            
        subtotal = Decimal("0.00")
        order_items_to_create = []
        
        for item in order_req.items:
            prod = products_map[item.product_id]
            if prod.stock < item.quantity:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": f"Stock insuficiente para {prod.name}. Disponibles: {prod.stock}"}
                )
            
            # Descontar stock general y de sucursal
            prod.stock -= item.quantity
            if order_req.sucursal and prod.sucursal_stocks:
                suc_stock = prod.sucursal_stocks.get(order_req.sucursal, 0)
                prod.sucursal_stocks[order_req.sucursal] = max(0, suc_stock - item.quantity)
            db.add(prod)
            
            item_subtotal = Decimal(str(prod.price)) * Decimal(item.quantity)
            subtotal += item_subtotal
            
            order_items_to_create.append({
                "product_id": prod.id,
                "product_name": prod.name,
                "sku": prod.sku,
                "unit_price": Decimal(str(prod.price)),
                "quantity": item.quantity,
                "subtotal": item_subtotal
            })

        # IVA 15% (Ecuador)
        tax = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
        total = subtotal + tax

        # 2. Generar número de orden único
        clean_phone = order_req.customer_phone.replace("+", "").replace(" ", "").strip()
        random_suffix = random.randint(1000, 9999)
        order_number = f"CAST-{datetime.utcnow().year}-{random_suffix}"
        
        session_service = SessionService(db, redis_client)
        phone_hash = session_service.derive_phone_hash(clean_phone)

        # 3. Crear registro de Orden
        order = Order(
            order_number=order_number,
            phone_hash=phone_hash,
            customer_phone=clean_phone,
            customer_name=order_req.customer_name,
            delivery_type=order_req.delivery_type,
            delivery_address=order_req.delivery_address,
            sucursal=order_req.sucursal,
            status="created",
            payment_method=order_req.payment_method,
            subtotal=subtotal,
            tax=tax,
            total=total,
            notes=order_req.notes
        )
        db.add(order)
        await db.flush()

        # 4. Crear items de la orden
        for item_data in order_items_to_create:
            oi = OrderItem(
                order_id=order.id,
                product_id=item_data["product_id"],
                product_name=item_data["product_name"],
                sku=item_data["sku"],
                unit_price=item_data["unit_price"],
                quantity=item_data["quantity"],
                subtotal=item_data["subtotal"]
            )
            db.add(oi)

        await db.commit()
        logger.info(f"Orden creada exitosamente: {order_number} para {clean_phone} por ${total}")

        # 5. Enviar mensaje de WhatsApp al cliente
        items_summary_lines = []
        for it in order_items_to_create:
            items_summary_lines.append(f"• {it['quantity']}x *{it['product_name']}* (${it['subtotal']:.2f})")
        items_text = "\n".join(items_summary_lines)

        delivery_info = f"📍 *Retiro en Sucursal:* {order_req.sucursal}" if order_req.delivery_type == "pickup" else f"🚚 *Envío a Domicilio:* {order_req.delivery_address}"

        wa_message = (
            f"🛒 *¡PEDIDO CONFIRMADO CON ÉXITO!* 🦫\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *N° de Pedido:* `{order_number}`\n"
            f"👤 *Cliente:* {order_req.customer_name}\n"
            f"{delivery_info}\n"
            f"💳 *Pago:* {order_req.payment_method.capitalize()}\n\n"
            f"📦 *Productos:*\n"
            f"{items_text}\n\n"
            f"💵 *Subtotal:* ${subtotal:.2f}\n"
            f"📊 *IVA (15%):* ${tax:.2f}\n"
            f"💰 *TOTAL:* *${total:.2f}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ *Estado actual:* ⏳ *Preparando pedido (Picking)*\n\n"
            f"Puedes consultar el estado en cualquier momento con el botón *📦 Mi pedido* o escribiendo *{order_number}*."
        )

        # Enviar WhatsApp usando el gateway
        try:
            gateway_url = os.getenv("WHATSAPP_GATEWAY_URL", "http://whatsapp-gateway:8090")
            headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{gateway_url}/send",
                    json={"phone": clean_phone, "message": wa_message},
                    headers=headers,
                    timeout=10.0
                )
        except Exception as wa_err:
            logger.error(f"Error enviando confirmación de pedido por WhatsApp: {wa_err}")

        # 6. Sincronizar en Chatwoot como Nota Privada
        chatwoot = ChatwootService()
        if chatwoot.is_configured:
            try:
                cw_contact_id = await chatwoot.get_or_create_contact(clean_phone, f"Cliente {order_req.customer_name}")
                if cw_contact_id:
                    cw_conv_id = await chatwoot.get_or_create_conversation(cw_contact_id)
                    if cw_conv_id:
                        note = (
                            f"🛍️ *NUEVO PEDIDO DESDE CATÁLOGO WEB* 🛒\n\n"
                            f"• *Pedido:* {order_number}\n"
                            f"• *Cliente:* {order_req.customer_name} (+{clean_phone})\n"
                            f"• *Entrega:* {order_req.delivery_type.upper()} ({order_req.sucursal or order_req.delivery_address})\n"
                            f"• *Total:* ${total:.2f}\n\n"
                            f"📦 *Items:*\n{items_text}"
                        )
                        await chatwoot.post_message(cw_conv_id, note, is_private=True)
            except Exception as cw_err:
                logger.error(f"Error sincronizando orden con Chatwoot: {cw_err}")

        return {
            "success": True,
            "data": {
                "order_number": order_number,
                "total": float(total),
                "subtotal": float(subtotal),
                "tax": float(tax),
                "status": "created",
                "customer_name": order_req.customer_name,
                "delivery_type": order_req.delivery_type,
                "items_count": len(order_items_to_create)
            },
            "message": "¡Tu pedido ha sido registrado con éxito!"
        }

    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": f"Error al procesar el pedido: {str(e)}"})

@router.get("/api/catalog/orders/{order_number}")
async def get_order_status(order_number: str, db: AsyncSession = Depends(get_db_session)):
    """Consulta el estado de un pedido por su número de orden."""
    try:
        clean_num = order_number.strip().upper().replace("#", "")
        stmt = select(Order).where(Order.order_number == clean_num)
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        
        if not order:
            return JSONResponse(status_code=404, content={"success": False, "message": f"No se encontró el pedido {clean_num}"})
            
        # Obtener items
        stmt_items = select(OrderItem).where(OrderItem.order_id == order.id)
        res_items = await db.execute(stmt_items)
        items = res_items.scalars().all()
        
        STATUS_MAP = {
            "created": "Pedido recibido",
            "picking": "En preparación (Bodega)",
            "dispatched": "Despachado",
            "in_route": "En ruta de entrega",
            "delivered": "Entregado",
            "cancelled": "Cancelado"
        }
        
        return {
            "success": True,
            "data": {
                "order_number": order.order_number,
                "status": order.status,
                "status_display": STATUS_MAP.get(order.status, order.status),
                "customer_name": order.customer_name,
                "delivery_type": order.delivery_type,
                "sucursal": order.sucursal,
                "delivery_address": order.delivery_address,
                "subtotal": float(order.subtotal),
                "tax": float(order.tax),
                "total": float(order.total),
                "payment_method": order.payment_method,
                "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else None,
                "items": [
                    {
                        "product_name": it.product_name,
                        "sku": it.sku,
                        "quantity": it.quantity,
                        "unit_price": float(it.unit_price),
                        "subtotal": float(it.subtotal)
                    }
                    for it in items
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error querying order {order_number}: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al consultar la orden"})

# ─── Webview HTML Móvil (WhatsApp In-App Browser) ──────────────

@router.get("/catalogo", response_class=HTMLResponse)
async def serve_catalog_webview(
    phone: Optional[str] = Query(None),
    sucursal: Optional[str] = Query("Centro")
):
    """Servicio de la interfaz interactiva móvil para WhatsApp (Catálogo y Carrito)."""
    return HTMLResponse(content=CATALOG_HTML_TEMPLATE)

CATALOG_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es" class="h-full bg-slate-50">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Catálogo Ferretería Castor 🦫</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    /* Custom scrollbar & mobile optimization */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    .category-pill.active { background-color: #0f766e; color: white; font-weight: 600; shadow: 0 4px 6px -1px rgba(15, 118, 110, 0.2); }
    .no-select { user-select: none; -webkit-user-select: none; }
    .animate-pop { animation: pop 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
    @keyframes pop { 0% { transform: scale(0.95); } 100% { transform: scale(1); } }
  </style>
</head>
<body class="h-full flex flex-col font-sans text-slate-800 antialiased selection:bg-teal-500 selection:text-white pb-20">

  <!-- Header Fijo Superior -->
  <header class="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 py-3 shadow-sm">
    <div class="max-w-2xl mx-auto flex items-center justify-between gap-3">
      <div class="flex items-center gap-2.5">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-700 to-emerald-600 flex items-center justify-center text-white shadow-md shadow-teal-700/20">
          <span class="text-xl">🦫</span>
        </div>
        <div>
          <h1 class="font-bold text-slate-900 text-base leading-tight">Ferretería Castor</h1>
          <p class="text-xs text-teal-700 font-medium flex items-center gap-1">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Catálogo e Inventario
          </p>
        </div>
      </div>

      <!-- Botón Carrito con Badge -->
      <button onclick="openCartDrawer()" class="relative p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition active:scale-95">
        <i class="fa-solid fa-cart-shopping text-lg text-teal-800"></i>
        <span id="cart-badge" class="hidden absolute -top-1.5 -right-1.5 bg-red-500 text-white font-bold text-[11px] w-5 h-5 rounded-full flex items-center justify-center shadow-md animate-bounce">0</span>
      </button>
    </div>

    <!-- Buscador Integrado -->
    <div class="max-w-2xl mx-auto mt-2.5 relative">
      <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
      <input 
        id="search-input" 
        type="text" 
        placeholder="Buscar taladros, cemento, pinturas, tuberías..." 
        class="w-full bg-slate-100 border border-slate-200 rounded-xl pl-9 pr-8 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:bg-white transition shadow-inner"
        oninput="handleSearch(this.value)"
      >
      <button id="clear-search" onclick="clearSearch()" class="hidden absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
        <i class="fa-solid fa-circle-xmark text-sm"></i>
      </button>
    </div>

    <!-- Filtros de Categorías Horizontales -->
    <div class="max-w-2xl mx-auto mt-2.5 flex items-center gap-2 overflow-x-auto no-scrollbar py-1 text-xs">
      <button onclick="selectCategory('Todos')" class="category-pill active px-3.5 py-1.5 rounded-lg border border-slate-200 whitespace-nowrap transition">
        <i class="fa-solid fa-layer-group mr-1 text-[11px]"></i> Todos
      </button>
      <button onclick="selectCategory('Herramientas Eléctricas')" class="category-pill bg-white text-slate-600 px-3.5 py-1.5 rounded-lg border border-slate-200 whitespace-nowrap transition">
        ⚡ Herramientas
      </button>
      <button onclick="selectCategory('Construcción')" class="category-pill bg-white text-slate-600 px-3.5 py-1.5 rounded-lg border border-slate-200 whitespace-nowrap transition">
        🧱 Construcción
      </button>
      <button onclick="selectCategory('Pinturas')" class="category-pill bg-white text-slate-600 px-3.5 py-1.5 rounded-lg border border-slate-200 whitespace-nowrap transition">
        🎨 Pinturas
      </button>
      <button onclick="selectCategory('Plomería')" class="category-pill bg-white text-slate-600 px-3.5 py-1.5 rounded-lg border border-slate-200 whitespace-nowrap transition">
        🚿 Plomería
      </button>
      <button onclick="selectCategory('Electricidad')" class="category-pill bg-white text-slate-600 px-3.5 py-1.5 rounded-lg border border-slate-200 whitespace-nowrap transition">
        💡 Electricidad
      </button>
    </div>
  </header>

  <!-- Contenedor Principal de Productos -->
  <main class="flex-1 max-w-2xl w-full mx-auto p-4">
    <!-- Indicador de Sucursal Actual -->
    <div class="flex items-center justify-between bg-teal-50 border border-teal-200/70 rounded-xl px-3.5 py-2 mb-3 text-xs text-teal-900 shadow-sm">
      <div class="flex items-center gap-2">
        <i class="fa-solid fa-location-dot text-teal-600 text-sm"></i>
        <span>Stock en sucursal:</span>
        <select id="sucursal-selector" onchange="changeSucursal(this.value)" class="bg-white border border-teal-300 rounded-md font-semibold text-teal-900 px-2 py-0.5 focus:outline-none focus:ring-1 focus:ring-teal-500">
          <option value="Centro" selected>Sucursal Centro (Principal)</option>
          <option value="Norte">Sucursal Norte (Av. Eloy Alfaro)</option>
          <option value="Sur">Sucursal Sur</option>
          <option value="Cumbayá">Sucursal Cumbayá</option>
        </select>
      </div>
    </div>

    <!-- Grid / Listado de Productos -->
    <div id="products-container" class="space-y-3">
      <!-- Loading Skeleton -->
      <div class="flex items-center gap-3 bg-white p-3.5 rounded-2xl border border-slate-200 animate-pulse">
        <div class="w-20 h-20 bg-slate-200 rounded-xl shrink-0"></div>
        <div class="flex-1 space-y-2">
          <div class="h-4 bg-slate-200 rounded w-3/4"></div>
          <div class="h-3 bg-slate-200 rounded w-1/2"></div>
          <div class="h-4 bg-slate-200 rounded w-1/4"></div>
        </div>
      </div>
      <div class="flex items-center gap-3 bg-white p-3.5 rounded-2xl border border-slate-200 animate-pulse">
        <div class="w-20 h-20 bg-slate-200 rounded-xl shrink-0"></div>
        <div class="flex-1 space-y-2">
          <div class="h-4 bg-slate-200 rounded w-3/4"></div>
          <div class="h-3 bg-slate-200 rounded w-1/2"></div>
          <div class="h-4 bg-slate-200 rounded w-1/4"></div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div id="empty-state" class="hidden text-center py-12">
      <div class="w-16 h-16 bg-slate-100 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-3 text-2xl">
        <i class="fa-solid fa-box-open"></i>
      </div>
      <h3 class="font-semibold text-slate-800 text-base">No encontramos productos</h3>
      <p class="text-xs text-slate-500 mt-1">Prueba con otra palabra clave o selecciona otra categoría.</p>
    </div>
  </main>

  <!-- Barra Flotante Inferior de Resumen de Carrito -->
  <div id="floating-cart-bar" class="hidden fixed bottom-3 left-4 right-4 max-w-2xl mx-auto z-20">
    <button onclick="openCartDrawer()" class="w-full bg-gradient-to-r from-teal-700 to-emerald-700 text-white rounded-2xl p-3.5 flex items-center justify-between shadow-xl shadow-teal-900/30 active:scale-[0.98] transition">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center font-bold text-sm">
          <span id="floating-cart-count">0</span>
        </div>
        <span class="font-medium text-sm">Ver Carrito de Compras</span>
      </div>
      <div class="flex items-center gap-1.5 font-bold text-base">
        <span id="floating-cart-total">$0.00</span>
        <i class="fa-solid fa-chevron-right text-xs ml-1"></i>
      </div>
    </button>
  </div>

  <!-- Modal / Drawer Lateral de Carrito -->
  <div id="cart-drawer-backdrop" onclick="closeCartDrawer()" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 transition-opacity"></div>
  <div id="cart-drawer" class="fixed inset-y-0 right-0 max-w-md w-full bg-white shadow-2xl z-50 transform translate-x-full transition-transform duration-300 flex flex-col">
    <!-- Header del Carrito -->
    <div class="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-teal-100 text-teal-800 flex items-center justify-center text-sm font-bold">
          <i class="fa-solid fa-cart-shopping"></i>
        </div>
        <div>
          <h2 class="font-bold text-slate-900 text-base">Tu Carrito</h2>
          <p class="text-xs text-slate-500" id="cart-drawer-items-count">0 artículos</p>
        </div>
      </div>
      <button onclick="closeCartDrawer()" class="w-8 h-8 rounded-full bg-slate-200/70 hover:bg-slate-300 text-slate-600 flex items-center justify-center transition">
        <i class="fa-solid fa-xmark text-sm"></i>
      </button>
    </div>

    <!-- Lista de Items en Carrito -->
    <div id="cart-items-list" class="flex-1 overflow-y-auto p-4 space-y-3 divide-y divide-slate-100">
      <!-- Items renderizados dinámicamente -->
    </div>

    <!-- Footer con Totales y Checkout -->
    <div class="p-4 border-t border-slate-200 bg-slate-50 space-y-3">
      <!-- Opciones de Entrega -->
      <div class="space-y-2">
        <label class="text-xs font-semibold text-slate-700">Tipo de Entrega:</label>
        <div class="grid grid-cols-2 gap-2 text-xs">
          <button type="button" onclick="setDeliveryType('pickup')" id="btn-delivery-pickup" class="py-2 px-2.5 rounded-xl border border-teal-600 bg-teal-50 text-teal-800 font-semibold flex items-center justify-center gap-1.5 transition">
            <i class="fa-solid fa-store"></i> Retiro en Local
          </button>
          <button type="button" onclick="setDeliveryType('delivery')" id="btn-delivery-home" class="py-2 px-2.5 rounded-xl border border-slate-200 bg-white text-slate-600 font-medium flex items-center justify-center gap-1.5 transition">
            <i class="fa-solid fa-truck-fast"></i> A Domicilio
          </button>
        </div>
      </div>

      <!-- Dirección si es entrega a domicilio -->
      <div id="delivery-address-container" class="hidden space-y-1">
        <label class="text-xs font-semibold text-slate-700">Dirección de Entrega:</label>
        <input id="input-delivery-address" type="text" placeholder="Ej: Av. 10 de Agosto y Colón, Edif. 4..." class="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-teal-600 focus:outline-none">
      </div>

      <!-- Datos del Cliente -->
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="space-y-1">
          <label class="font-semibold text-slate-700">Tu Nombre:</label>
          <input id="input-customer-name" type="text" placeholder="Nombre y apellido" class="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs focus:ring-2 focus:ring-teal-600 focus:outline-none">
        </div>
        <div class="space-y-1">
          <label class="font-semibold text-slate-700">WhatsApp:</label>
          <input id="input-customer-phone" type="tel" placeholder="0984407038" class="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs focus:ring-2 focus:ring-teal-600 focus:outline-none">
        </div>
      </div>

      <!-- Método de Pago -->
      <div class="space-y-1">
        <label class="text-xs font-semibold text-slate-700">Forma de Pago:</label>
        <select id="input-payment-method" class="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs focus:ring-2 focus:ring-teal-600 focus:outline-none font-medium text-slate-800">
          <option value="efectivo">💵 Efectivo contra entrega</option>
          <option value="transferencia">🏦 Transferencia Bancaria (Pichincha / Guayaquil)</option>
          <option value="tarjeta">💳 Tarjeta de Débito / Crédito (+ Datafast)</option>
        </select>
      </div>

      <!-- Desglose de Precios -->
      <div class="bg-white p-3 rounded-xl border border-slate-200 space-y-1.5 text-xs">
        <div class="flex justify-between text-slate-500">
          <span>Subtotal:</span>
          <span id="cart-subtotal" class="font-medium">$0.00</span>
        </div>
        <div class="flex justify-between text-slate-500">
          <span>IVA (15%):</span>
          <span id="cart-tax" class="font-medium">$0.00</span>
        </div>
        <div class="flex justify-between text-sm font-bold text-slate-900 pt-1 border-t border-slate-100">
          <span>Total a Pagar:</span>
          <span id="cart-total" class="text-teal-800 text-base">$0.00</span>
        </div>
      </div>

      <!-- Botón Confirmar Orden -->
      <button id="btn-submit-order" onclick="submitOrder()" class="w-full bg-teal-700 hover:bg-teal-800 text-white font-bold py-3 px-4 rounded-xl shadow-lg shadow-teal-900/20 active:scale-[0.98] transition flex items-center justify-center gap-2">
        <i class="fa-solid fa-check"></i>
        <span>Confirmar Pedido y Enviar a WhatsApp</span>
      </button>
    </div>
  </div>

  <!-- Modal de Pedido Exitoso -->
  <div id="success-modal" class="hidden fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-3xl p-6 max-w-sm w-full text-center shadow-2xl animate-pop border border-slate-100">
      <div class="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-3.5 text-3xl shadow-md shadow-emerald-500/10">
        <i class="fa-solid fa-circle-check"></i>
      </div>
      <h3 class="text-lg font-bold text-slate-900">¡Pedido Recibido! 🎉</h3>
      <p class="text-xs text-slate-500 mt-1">Hemos registrado tu orden y te enviamos el comprobante directamente a tu WhatsApp.</p>
      
      <div class="my-4 p-3 bg-slate-50 rounded-xl border border-slate-200 text-left text-xs space-y-1">
        <div class="flex justify-between">
          <span class="text-slate-500">N° de Pedido:</span>
          <span id="success-order-id" class="font-bold text-slate-800">#CAST-2026-0000</span>
        </div>
        <div class="flex justify-between">
          <span class="text-slate-500">Total:</span>
          <span id="success-order-total" class="font-bold text-teal-700">$0.00</span>
        </div>
        <div class="flex justify-between">
          <span class="text-slate-500">Estado:</span>
          <span class="font-semibold text-amber-600">⏳ En preparación</span>
        </div>
      </div>

      <button onclick="closeSuccessAndReturn()" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl shadow-lg shadow-emerald-600/20 transition active:scale-95 flex items-center justify-center gap-2 text-sm">
        <i class="fa-brands fa-whatsapp text-lg"></i>
        <span>Regresar al Chat de WhatsApp</span>
      </button>
    </div>
  </div>

  <!-- JavaScript de la Aplicación -->
  <script>
    // Variables de Estado
    let allProducts = [];
    let currentCategory = 'Todos';
    let currentSearch = '';
    let currentSucursal = 'Centro';
    let cart = {}; // { productId: { product, quantity } }
    let deliveryType = 'pickup';

    // Parse URL params (phone prefill)
    const urlParams = new URLSearchParams(window.location.search);
    const paramPhone = urlParams.get('phone') || '';
    const paramSucursal = urlParams.get('sucursal') || 'Centro';

    if (paramPhone) {
      document.getElementById('input-customer-phone').value = paramPhone;
    }
    if (paramSucursal) {
      document.getElementById('sucursal-selector').value = paramSucursal;
      currentSucursal = paramSucursal;
    }

    // Inicialización
    document.addEventListener('DOMContentLoaded', () => {
      fetchProducts();
    });

    async function fetchProducts() {
      try {
        const res = await fetch(`/api/catalog/products?sucursal=${encodeURIComponent(currentSucursal)}`);
        const json = await res.json();
        if (json.success) {
          allProducts = json.data;
          renderProducts();
        }
      } catch (err) {
        console.error('Error fetching products:', err);
      }
    }

    function renderProducts() {
      const container = document.getElementById('products-container');
      const emptyState = document.getElementById('empty-state');
      
      const filtered = allProducts.filter(p => {
        const matchesCat = (currentCategory === 'Todos' || p.category.toLowerCase() === currentCategory.toLowerCase());
        const matchesSearch = !currentSearch || 
          p.name.toLowerCase().includes(currentSearch.toLowerCase()) || 
          p.description.toLowerCase().includes(currentSearch.toLowerCase()) ||
          p.sku.toLowerCase().includes(currentSearch.toLowerCase());
        return matchesCat && matchesSearch;
      });

      if (filtered.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
      }

      emptyState.classList.add('hidden');
      container.innerHTML = filtered.map(p => {
        const qtyInCart = cart[p.id] ? cart[p.id].quantity : 0;
        const sucStock = p.sucursal_stocks ? (p.sucursal_stocks[currentSucursal] || 0) : p.stock;
        const inStock = sucStock > 0;

        return `
          <div class="bg-white p-3.5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between gap-3 hover:border-teal-500/50 transition">
            <!-- Imagen con Fallback -->
            <div class="w-20 h-20 bg-slate-100 rounded-xl overflow-hidden shrink-0 border border-slate-100 flex items-center justify-center relative">
              <img src="${p.image_url}" alt="${p.name}" class="w-full h-full object-cover" onerror="this.src='https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=600&auto=format&fit=crop&q=80'">
              ${!inStock ? '<span class="absolute inset-0 bg-slate-900/60 text-[10px] text-white font-bold flex items-center justify-center text-center p-1 leading-tight">Agotado</span>' : ''}
            </div>

            <!-- Detalles del Producto -->
            <div class="flex-1 min-w-0">
              <span class="text-[10px] uppercase font-bold text-teal-700 tracking-wider">${p.category}</span>
              <h3 class="font-bold text-slate-900 text-xs sm:text-sm leading-tight truncate mt-0.5" title="${p.name}">${p.name}</h3>
              <p class="text-[11px] text-slate-500 line-clamp-1 mt-0.5">${p.description || ''}</p>
              
              <div class="flex items-center gap-2 mt-1.5">
                <span class="font-extrabold text-slate-900 text-sm sm:text-base">$${p.price.toFixed(2)}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded ${inStock ? 'bg-emerald-50 text-emerald-700 font-medium' : 'bg-red-50 text-red-600 font-medium'}">
                  ${inStock ? `${sucStock} disp.` : 'Sin stock'}
                </span>
              </div>
            </div>

            <!-- Contador de Cantidad Interactivo (- 0 +) Estilo jelou.ia -->
            <div class="shrink-0 flex items-center bg-slate-100/90 rounded-xl border border-slate-200/90 p-1">
              <button onclick="updateItemQuantity('${p.id}', -1)" ${qtyInCart === 0 ? 'disabled' : ''} class="w-7 h-7 rounded-lg bg-white text-slate-700 shadow-sm flex items-center justify-center font-bold text-sm disabled:opacity-30 disabled:cursor-not-allowed active:scale-90 transition">
                −
              </button>
              <span class="w-6 text-center font-bold text-xs text-slate-800 no-select" id="qty-badge-${p.id}">
                ${qtyInCart}
              </span>
              <button onclick="updateItemQuantity('${p.id}', 1)" ${!inStock ? 'disabled' : ''} class="w-7 h-7 rounded-lg bg-teal-700 text-white shadow-sm flex items-center justify-center font-bold text-sm disabled:opacity-30 disabled:cursor-not-allowed active:scale-90 transition hover:bg-teal-800">
                +
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function selectCategory(cat) {
      currentCategory = cat;
      document.querySelectorAll('.category-pill').forEach(btn => {
        if (btn.innerText.includes(cat) || (cat === 'Todos' && btn.innerText.includes('Todos'))) {
          btn.className = 'category-pill active px-3.5 py-1.5 rounded-lg border border-teal-700 whitespace-nowrap transition';
        } else {
          btn.className = 'category-pill bg-white text-slate-600 px-3.5 py-1.5 rounded-lg border border-slate-200 whitespace-nowrap transition';
        }
      });
      renderProducts();
    }

    function handleSearch(val) {
      currentSearch = val;
      const clearBtn = document.getElementById('clear-search');
      if (val.trim()) {
        clearBtn.classList.remove('hidden');
      } else {
        clearBtn.classList.add('hidden');
      }
      renderProducts();
    }

    function clearSearch() {
      document.getElementById('search-input').value = '';
      handleSearch('');
    }

    function changeSucursal(val) {
      currentSucursal = val;
      renderProducts();
    }

    function updateItemQuantity(prodId, delta) {
      const prod = allProducts.find(p => p.id === prodId);
      if (!prod) return;

      const currentQty = cart[prodId] ? cart[prodId].quantity : 0;
      const newQty = currentQty + delta;

      if (newQty <= 0) {
        delete cart[prodId];
      } else {
        cart[prodId] = {
          product: prod,
          quantity: newQty
        };
      }

      // Actualizar UI
      const badge = document.getElementById(`qty-badge-${prodId}`);
      if (badge) badge.innerText = Math.max(0, newQty);
      
      updateCartSummary();
      renderProducts();
    }

    function updateCartSummary() {
      let count = 0;
      let subtotal = 0;

      Object.values(cart).forEach(item => {
        count += item.quantity;
        subtotal += item.product.price * item.quantity;
      });

      const tax = subtotal * 0.15;
      const total = subtotal + tax;

      // Header Badge
      const cartBadge = document.getElementById('cart-badge');
      if (count > 0) {
        cartBadge.innerText = count;
        cartBadge.classList.remove('hidden');
      } else {
        cartBadge.classList.add('hidden');
      }

      // Floating bottom bar
      const floatingBar = document.getElementById('floating-cart-bar');
      if (count > 0) {
        floatingBar.classList.remove('hidden');
        document.getElementById('floating-cart-count').innerText = count;
        document.getElementById('floating-cart-total').innerText = `$${total.toFixed(2)}`;
      } else {
        floatingBar.classList.add('hidden');
      }

      // Drawer totals
      document.getElementById('cart-drawer-items-count').innerText = `${count} artículos`;
      document.getElementById('cart-subtotal').innerText = `$${subtotal.toFixed(2)}`;
      document.getElementById('cart-tax').innerText = `$${tax.toFixed(2)}`;
      document.getElementById('cart-total').innerText = `$${total.toFixed(2)}`;

      renderCartDrawerItems();
    }

    function renderCartDrawerItems() {
      const container = document.getElementById('cart-items-list');
      const items = Object.values(cart);

      if (items.length === 0) {
        container.innerHTML = `
          <div class="text-center py-10">
            <div class="w-14 h-14 bg-slate-100 text-slate-300 rounded-full flex items-center justify-center mx-auto mb-2 text-xl">
              <i class="fa-solid fa-cart-shopping"></i>
            </div>
            <p class="font-medium text-slate-700 text-sm">Tu carrito está vacío</p>
            <p class="text-xs text-slate-400 mt-0.5">Agrega productos del catálogo para armar tu pedido.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = items.map(it => `
        <div class="flex items-center justify-between gap-3 pt-3 first:pt-0">
          <div class="flex-1 min-w-0">
            <h4 class="font-bold text-xs text-slate-900 truncate">${it.product.name}</h4>
            <p class="text-[11px] text-teal-700 font-semibold">$${it.product.price.toFixed(2)} c/u</p>
          </div>

          <!-- Stepper -->
          <div class="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200">
            <button onclick="updateItemQuantity('${it.product.id}', -1)" class="w-6 h-6 rounded bg-white text-slate-700 flex items-center justify-center text-xs font-bold shadow-sm active:scale-90">
              −
            </button>
            <span class="w-6 text-center font-bold text-xs text-slate-800">${it.quantity}</span>
            <button onclick="updateItemQuantity('${it.product.id}', 1)" class="w-6 h-6 rounded bg-teal-700 text-white flex items-center justify-center text-xs font-bold shadow-sm active:scale-90">
              +
            </button>
          </div>

          <span class="font-bold text-xs text-slate-900 w-14 text-right">
            $${(it.product.price * it.quantity).toFixed(2)}
          </span>
        </div>
      `).join('');
    }

    function openCartDrawer() {
      document.getElementById('cart-drawer-backdrop').classList.remove('hidden');
      document.getElementById('cart-drawer').classList.remove('translate-x-full');
      updateCartSummary();
    }

    function closeCartDrawer() {
      document.getElementById('cart-drawer-backdrop').classList.add('hidden');
      document.getElementById('cart-drawer').classList.add('translate-x-full');
    }

    function setDeliveryType(type) {
      deliveryType = type;
      const btnPickup = document.getElementById('btn-delivery-pickup');
      const btnHome = document.getElementById('btn-delivery-home');
      const addressContainer = document.getElementById('delivery-address-container');

      if (type === 'pickup') {
        btnPickup.className = 'py-2 px-2.5 rounded-xl border border-teal-600 bg-teal-50 text-teal-800 font-semibold flex items-center justify-center gap-1.5 transition';
        btnHome.className = 'py-2 px-2.5 rounded-xl border border-slate-200 bg-white text-slate-600 font-medium flex items-center justify-center gap-1.5 transition';
        addressContainer.classList.add('hidden');
      } else {
        btnHome.className = 'py-2 px-2.5 rounded-xl border border-teal-600 bg-teal-50 text-teal-800 font-semibold flex items-center justify-center gap-1.5 transition';
        btnPickup.className = 'py-2 px-2.5 rounded-xl border border-slate-200 bg-white text-slate-600 font-medium flex items-center justify-center gap-1.5 transition';
        addressContainer.classList.remove('hidden');
      }
    }

    async function submitOrder() {
      const items = Object.entries(cart).map(([pid, item]) => ({
        product_id: pid,
        quantity: item.quantity
      }));

      if (items.length === 0) {
        alert('Por favor agrega al menos un producto al carrito.');
        return;
      }

      const name = document.getElementById('input-customer-name').value.trim();
      const phone = document.getElementById('input-customer-phone').value.trim();
      const address = document.getElementById('input-delivery-address').value.trim();
      const paymentMethod = document.getElementById('input-payment-method').value;

      if (!name) {
        alert('Por favor ingresa tu nombre.');
        document.getElementById('input-customer-name').focus();
        return;
      }

      if (!phone || phone.length < 8) {
        alert('Por favor ingresa un número de WhatsApp válido.');
        document.getElementById('input-customer-phone').focus();
        return;
      }

      if (deliveryType === 'delivery' && !address) {
        alert('Por favor ingresa la dirección de entrega.');
        document.getElementById('input-delivery-address').focus();
        return;
      }

      const btnSubmit = document.getElementById('btn-submit-order');
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Procesando pedido...';

      try {
        const payload = {
          customer_name: name,
          customer_phone: phone,
          delivery_type: deliveryType,
          delivery_address: deliveryType === 'delivery' ? address : null,
          sucursal: currentSucursal,
          payment_method: paymentMethod,
          items: items
        };

        const res = await fetch('/api/catalog/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const json = await res.json();
        if (json.success) {
          // Mostrar modal de éxito
          document.getElementById('success-order-id').innerText = json.data.order_number;
          document.getElementById('success-order-total').innerText = `$${json.data.total.toFixed(2)}`;
          document.getElementById('success-modal').classList.remove('hidden');
          
          // Limpiar Carrito
          cart = {};
          updateCartSummary();
          closeCartDrawer();
        } else {
          alert('No fue posible crear la orden: ' + json.message);
        }
      } catch (err) {
        console.error('Error creating order:', err);
        alert('Error de conexión al enviar el pedido. Por favor intenta de nuevo.');
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = '<i class="fa-solid fa-check"></i> Confirmar Pedido y Enviar a WhatsApp';
      }
    }

    function closeSuccessAndReturn() {
      document.getElementById('success-modal').classList.add('hidden');
      // Cerrar Webview si está en WhatsApp o redirigir al chat
      window.location.href = 'https://wa.me/';
    }
  </script>
</body>
</html>
"""
