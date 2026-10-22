"""
Vehicles API Router — Auto Dealership Ecuador (2026)
Handles vehicle catalog queries, financing simulations, and lead tracking from WhatsApp and the mobile webview.
"""
import logging
import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.tables import Vehicle, VehicleLead
from app.services.chatwoot_service import ChatwootService

logger = logging.getLogger("backend.api.vehicles")
router = APIRouter()

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


# ── Leads & Interacción Seguimiento ───────────────────────────────────

@router.post("/api/v1/vehicles/lead", tags=["Vehículos Ecuador"])
async def create_vehicle_lead(payload: VehicleLeadCreate, db: AsyncSession = Depends(get_db_session)):
    """Registra una cotización o solicitud de Test Drive en la base de datos y la sincroniza con Chatwoot."""
    clean_phone = payload.customer_phone.replace("+", "").strip()
    phone_hash = str(uuid.uuid5(uuid.NAMESPACE_DNS, clean_phone))

    vehicle_id = None
    model_name = None
    if payload.vehicle_code:
        v_res = await db.execute(select(Vehicle).where(Vehicle.code == payload.vehicle_code))
        veh = v_res.scalar_one_or_none()
        if veh:
            vehicle_id = veh.id
            model_name = f"{veh.brand} {veh.model}"

    lead_code = f"LEAD-AUTO-{uuid.uuid4().hex[:6].upper()}"

    lead = VehicleLead(
        lead_code=lead_code,
        customer_phone=clean_phone,
        phone_hash=phone_hash,
        customer_name=payload.customer_name,
        city=payload.city,
        interested_vehicle_id=vehicle_id,
        interested_model_name=model_name or "Modelo por definir",
        quote_type=payload.quote_type,
        down_payment_offered=payload.down_payment_offered,
        term_months=payload.term_months,
        test_drive_requested=payload.test_drive_requested,
        status="nuevo",
        notes=payload.notes
    )

    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Notificar y registrar en Chatwoot para auditoría del Gerente
    try:
        cw = ChatwootService()
        if cw.is_configured:
            contact_id = await cw.get_or_create_contact(clean_phone, payload.customer_name or f"Lead {clean_phone}")
            if contact_id:
                cw_conv_id = await cw.get_or_create_conversation(contact_id)
                if cw_conv_id:
                    note = f"🚗 NUEVO LEAD AUTOMOTRIZ:\n" \
                           f"• Código: {lead_code}\n" \
                           f"• Vehículo: {model_name or 'No especificado'}\n" \
                           f"• Tipo: {payload.quote_type}\n" \
                           f"• Entrada: ${payload.down_payment_offered or 0}\n" \
                           f"• Test Drive: {'SÍ' if payload.test_drive_requested else 'No'}\n" \
                           f"• Ciudad: {payload.city}"
                    await cw.post_message(cw_conv_id, note, message_type="incoming")
                    lead.chatwoot_conversation_id = cw_conv_id
                    await db.commit()
    except Exception as e:
        logger.error(f"Error sincronizando lead con Chatwoot: {e}")

    return {
        "status": "success",
        "lead_code": lead_code,
        "message": f"Lead registrado con éxito para {model_name or 'vehículo'}.",
        "lead_id": str(lead.id)
    }
