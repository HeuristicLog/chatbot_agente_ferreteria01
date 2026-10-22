"""
Vehicles API Router — Auto Dealership Ecuador (2026)
Handles vehicle catalog queries, financing simulations, in-app garage/cart, and quote tracking from WhatsApp and the mobile webview.
"""
import logging
import os
import uuid
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from pydantic import BaseModel
import httpx

from app.db.session import get_db_session
from app.db.tables import Vehicle, VehicleLead, VehicleCartItem, VehicleQuote
from app.services.chatwoot_service import ChatwootService
from app.config import settings

logger = logging.getLogger("backend.api.vehicles")
router = APIRouter()

GATEWAY_URL = "http://whatsapp-gateway:8090"

# ── Schemas ─────────────────────────────────────────────────────────────

class VehicleLeadCreate(BaseModel):
    customer_phone: str
    customer_name: Optional[str] = "Cliente WhatsApp"
    city: Optional[str] = "Quito"
    vehicle_code: Optional[str] = None
    quote_type: Optional[str] = "credito"
    down_payment_offered: Optional[float] = None
    term_months: Optional[int] = 48
    test_drive_requested: Optional[bool] = False
    notes: Optional[str] = None

class VehicleCartItemCreate(BaseModel):
    customer_phone: str
    vehicle_code: str
    down_payment_percent: Optional[int] = 20
    down_payment_amount: Optional[float] = 0.0
    term_months: Optional[int] = 48
    estimated_monthly_fee: Optional[float] = 0.0

class VehicleQuoteCreate(BaseModel):
    customer_phone: str
    customer_name: Optional[str] = "Cliente WhatsApp"
    city: Optional[str] = "Quito"
    vehicle_code: str
    down_payment_percent: Optional[int] = 20
    down_payment_amount: float
    term_months: int = 48
    monthly_fee: float
    insurance_included: bool = True
    trade_in_used_car: bool = False
    used_car_details: Optional[str] = None


# ── Webview Endpoint ───────────────────────────────────────────────────

@router.get("/catalogo-autos", response_class=HTMLResponse, tags=["Vehículos Ecuador"])
@router.get("/autos", response_class=HTMLResponse, tags=["Vehículos Ecuador"])
async def serve_autos_catalog():
    """Sirve la pantalla emergente e-commerce interactiva de autos nuevos para WhatsApp."""
    container_path = "/app/catalogo_autos.html"
    local_path = "C:/Users/User/Desktop/KEVIN/ChatbotFlowise/catalogo_autos.html"
    
    if os.path.exists(container_path):
        with open(container_path, "r", encoding="utf-8") as f:
            return f.read()
    elif os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return "<h1>Catálogo de Vehículos no encontrado en el servidor.</h1>"


# ── Catalog APIs ───────────────────────────────────────────────────────

@router.get("/api/v1/vehicles", tags=["Vehículos Ecuador"])
async def list_vehicles(
    brand: Optional[str] = Query(None, description="Filtrar por marca (Chevrolet, Kia, Toyota, etc.)"),
    body_type: Optional[str] = Query(None, description="Filtrar por carrocería (SUV, Camioneta, Sedán)"),
    fuel_type: Optional[str] = Query(None, description="Filtrar por combustible (Gasolina, Diésel, Híbrido)"),
    max_price: Optional[float] = Query(None, description="Precio máximo en USD"),
    featured_only: bool = Query(False, description="Solo vehículos destacados"),
    db: AsyncSession = Depends(get_db_session)
):
    """Lista vehículos del catálogo de Ecuador con especificaciones completas."""
    query = select(Vehicle).where(Vehicle.is_active == True)

    if brand:
        query = query.where(Vehicle.brand.ilike(f"%{brand}%"))
    if body_type:
        query = query.where(Vehicle.body_type.ilike(f"%{body_type}%"))
    if fuel_type:
        query = query.where(Vehicle.fuel_type.ilike(f"%{fuel_type}%"))
    if max_price:
        query = query.where(Vehicle.price_usd <= max_price)
    if featured_only:
        query = query.where(Vehicle.is_featured == True)

    query = query.order_by(Vehicle.is_featured.desc(), Vehicle.price_usd.asc())
    result = await db.execute(query)
    vehicles = result.scalars().all()

    data = []
    for v in vehicles:
        data.append({
            "id": str(v.id),
            "code": v.code,
            "brand": v.brand,
            "model": v.model,
            "year": v.year,
            "body_type": v.body_type,
            "engine": v.engine,
            "fuel_type": v.fuel_type,
            "transmission": v.transmission,
            "traction": v.traction,
            "passenger_capacity": v.passenger_capacity,
            "trunk_capacity_liters": v.trunk_capacity_liters,
            "price_usd": float(v.price_usd),
            "min_down_payment": float(v.min_down_payment),
            "estimated_monthly_fee": float(v.estimated_monthly_fee),
            "description": v.description,
            "safety_features": v.safety_features or [],
            "equipment": v.equipment or [],
            "colors_available": v.colors_available or [],
            "image_url": v.image_url,
            "gallery_urls": v.gallery_urls or [],
            "stock_units": v.stock_units,
            "is_featured": v.is_featured
        })

    return {"status": "success", "count": len(data), "data": data}


@router.get("/api/v1/vehicles/{code}", tags=["Vehículos Ecuador"])
async def get_vehicle_by_code(code: str, db: AsyncSession = Depends(get_db_session)):
    """Obtiene la ficha técnica completa de un vehículo por su código."""
    query = select(Vehicle).where(Vehicle.code == code)
    res = await db.execute(query)
    v = res.scalar_one_or_none()

    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")

    return {
        "status": "success",
        "data": {
            "id": str(v.id),
            "code": v.code,
            "brand": v.brand,
            "model": v.model,
            "year": v.year,
            "body_type": v.body_type,
            "engine": v.engine,
            "fuel_type": v.fuel_type,
            "transmission": v.transmission,
            "traction": v.traction,
            "passenger_capacity": v.passenger_capacity,
            "trunk_capacity_liters": v.trunk_capacity_liters,
            "price_usd": float(v.price_usd),
            "min_down_payment": float(v.min_down_payment),
            "estimated_monthly_fee": float(v.estimated_monthly_fee),
            "description": v.description,
            "safety_features": v.safety_features,
            "equipment": v.equipment,
            "colors_available": v.colors_available,
            "image_url": v.image_url,
            "gallery_urls": v.gallery_urls,
            "stock_units": v.stock_units
        }
    }


# ── Garaje / Carrito de Cotización en Base de Datos ─────────────────────

@router.get("/api/v1/vehicles/cart/{phone}", tags=["Vehículos Ecuador - Garaje"])
async def get_customer_garage(phone: str, db: AsyncSession = Depends(get_db_session)):
    """Obtiene los vehículos guardados en el garaje/carrito del cliente."""
    clean_phone = phone.replace("+", "").replace(" ", "").strip()
    query = select(VehicleCartItem, Vehicle).join(Vehicle, VehicleCartItem.vehicle_id == Vehicle.id).where(
        VehicleCartItem.customer_phone == clean_phone,
        VehicleCartItem.status == "in_cart"
    ).order_by(VehicleCartItem.created_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    cart_items = []
    for cart_item, vehicle in rows:
        cart_items.append({
            "item_id": str(cart_item.id),
            "vehicle_code": vehicle.code,
            "brand": vehicle.brand,
            "model": vehicle.model,
            "year": vehicle.year,
            "body_type": vehicle.body_type,
            "image_url": vehicle.image_url,
            "price_usd": float(vehicle.price_usd),
            "down_payment_percent": cart_item.down_payment_percent,
            "down_payment_amount": float(cart_item.down_payment_amount),
            "term_months": cart_item.term_months,
            "estimated_monthly_fee": float(cart_item.estimated_monthly_fee),
            "created_at": cart_item.created_at.isoformat() if cart_item.created_at else None
        })
        
    return {"status": "success", "count": len(cart_items), "items": cart_items}


@router.post("/api/v1/vehicles/cart", tags=["Vehículos Ecuador - Garaje"])
async def add_to_customer_garage(payload: VehicleCartItemCreate, db: AsyncSession = Depends(get_db_session)):
    """Guarda un vehículo con su configuración de cuota en el garaje del cliente."""
    clean_phone = payload.customer_phone.replace("+", "").replace(" ", "").strip()
    
    v_res = await db.execute(select(Vehicle).where(Vehicle.code == payload.vehicle_code))
    vehicle = v_res.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        
    # Verificar si ya existe en su garaje
    existing_res = await db.execute(
        select(VehicleCartItem).where(
            VehicleCartItem.customer_phone == clean_phone,
            VehicleCartItem.vehicle_id == vehicle.id,
            VehicleCartItem.status == "in_cart"
        )
    )
    existing = existing_res.scalar_one_or_none()
    
    if existing:
        existing.down_payment_percent = payload.down_payment_percent
        existing.down_payment_amount = Decimal(str(payload.down_payment_amount))
        existing.term_months = payload.term_months
        existing.estimated_monthly_fee = Decimal(str(payload.estimated_monthly_fee))
        await db.commit()
        return {"status": "updated", "message": f"{vehicle.brand} {vehicle.model} actualizado en tu garaje."}
    
    new_item = VehicleCartItem(
        customer_phone=clean_phone,
        vehicle_id=vehicle.id,
        down_payment_percent=payload.down_payment_percent,
        down_payment_amount=Decimal(str(payload.down_payment_amount)),
        term_months=payload.term_months,
        estimated_monthly_fee=Decimal(str(payload.estimated_monthly_fee)),
        status="in_cart"
    )
    db.add(new_item)
    await db.commit()
    
    return {"status": "added", "message": f"{vehicle.brand} {vehicle.model} agregado a tu garaje."}


@router.delete("/api/v1/vehicles/cart/{item_id}", tags=["Vehículos Ecuador - Garaje"])
async def remove_from_customer_garage(item_id: str, db: AsyncSession = Depends(get_db_session)):
    """Elimina un vehículo del garaje/carrito."""
    try:
        uid = uuid.UUID(item_id)
        await db.execute(delete(VehicleCartItem).where(VehicleCartItem.id == uid))
        await db.commit()
        return {"status": "deleted", "message": "Vehículo removido del garaje."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Cotizaciones Formales & Notificación Automática ────────────────────

@router.post("/api/v1/vehicles/quote", tags=["Vehículos Ecuador - Cotizaciones"])
async def submit_formal_quote(payload: VehicleQuoteCreate, db: AsyncSession = Depends(get_db_session)):
    """
    Crea una cotización formal en la base de datos, envía confirmación a WhatsApp 
    y la sincroniza con el panel de Chatwoot para auditoría del Gerente y seguimiento comercial.
    """
    clean_phone = payload.customer_phone.replace("+", "").replace(" ", "").strip()
    
    v_res = await db.execute(select(Vehicle).where(Vehicle.code == payload.vehicle_code))
    vehicle = v_res.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
        
    quote_code = f"COT-AUTO-{uuid.uuid4().hex[:6].upper()}"
    total_price = Decimal(str(vehicle.price_usd))
    down_payment = Decimal(str(payload.down_payment_amount))
    financed_amount = total_price - down_payment
    
    quote = VehicleQuote(
        quote_code=quote_code,
        customer_phone=clean_phone,
        customer_name=payload.customer_name or "Cliente WhatsApp",
        city=payload.city or "Quito",
        vehicle_id=vehicle.id,
        vehicle_name=f"{vehicle.brand} {vehicle.model} ({vehicle.year})",
        vehicle_price=total_price,
        down_payment=down_payment,
        financed_amount=financed_amount,
        term_months=payload.term_months,
        monthly_fee=Decimal(str(payload.monthly_fee)),
        insurance_included=payload.insurance_included,
        trade_in_used_car=payload.trade_in_used_car,
        used_car_details=payload.used_car_details,
        status="pendiente"
    )
    
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    
    # 1. Enviar mensaje de confirmación a WhatsApp del cliente
    whatsapp_message = (
        f"🚗 *¡Cotización Oficial Generada con Éxito!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Código de Cotización:* `{quote_code}`\n"
        f"👤 *Cliente:* {payload.customer_name}\n"
        f"📍 *Ciudad:* {payload.city}\n\n"
        f"🚘 *Vehículo:* {vehicle.brand} {vehicle.model} ({vehicle.year})\n"
        f"💵 *Precio con IVA (15%):* ${float(total_price):,.2f} USD\n"
        f"💰 *Entrada propuesta:* ${float(down_payment):,.2f} ({payload.down_payment_percent}%)\n"
        f"📅 *Plazo:* {payload.term_months} meses\n"
        f"📊 *Cuota estimada:* ${float(payload.monthly_fee):,.2f} / mes\n"
        f"🛡️ *Seguro Todo Riesgo:* {'Incluido con GPS' if payload.insurance_included else 'No incluido'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ Tu solicitud de crédito ya está siendo procesada con nuestros bancos aliados (Banco Pichincha, Guayaquil, Produbanco).\n\n"
        f"Un asesor comercial se comunicará contigo en breve para coordinar tu *Prueba de Manejo (Test Drive)*."
    )
    
    try:
        headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}
        gw_payload = {"phone": clean_phone, "message": whatsapp_message}
        async with httpx.AsyncClient() as client:
            await client.post(f"{GATEWAY_URL}/send", json=gw_payload, headers=headers, timeout=8.0)
    except Exception as gw_err:
        logger.error(f"Error enviando confirmación de cotización por WhatsApp: {gw_err}")

    # 2. Sincronizar en Chatwoot para auditoría del Gerente
    try:
        cw = ChatwootService()
        if cw.is_configured:
            contact_id = await cw.get_or_create_contact(clean_phone, payload.customer_name or f"Cliente {clean_phone}")
            if contact_id:
                cw_conv_id = await cw.get_or_create_conversation(contact_id)
                if cw_conv_id:
                    note = (
                        f"🚗 *NUEVA COTIZACIÓN AUTOMOTRIZ GENERADA*\n"
                        f"• Código: {quote_code}\n"
                        f"• Auto: {vehicle.brand} {vehicle.model} ({vehicle.year})\n"
                        f"• Precio: ${float(total_price):,.2f} USD\n"
                        f"• Entrada: ${float(down_payment):,.2f} | Plazo: {payload.term_months}m\n"
                        f"• Cuota: ${float(payload.monthly_fee):,.2f}/mes\n"
                        f"• Retoma auto usado: {'SÍ: ' + (payload.used_car_details or '') if payload.trade_in_used_car else 'No'}\n"
                        f"• Ciudad: {payload.city}"
                    )
                    await cw.post_message(cw_conv_id, note, message_type="incoming")
                    quote.chatwoot_conversation_id = cw_conv_id
                    await db.commit()
    except Exception as cw_err:
        logger.error(f"Error sincronizando cotización con Chatwoot: {cw_err}")

    return {
        "status": "success",
        "quote_code": quote_code,
        "message": "Cotización guardada exitosamente y enviada a tu WhatsApp.",
        "quote_id": str(quote.id)
    }
