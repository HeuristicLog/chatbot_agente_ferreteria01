import logging
from fastapi import FastAPI, Depends, HTTPException, status, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import Dict, Any, List, Optional
from app.db.session import engine, get_db_session
from app.db.tables import Base, MockDriver, MockTicket, MockTicketEvent, MockLogisticOperation, MockStop, MockIncident

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mock-logistics-api")

app = FastAPI(
    title="Mock Logistics Production API",
    version="1.0.0",
    description="Local replica of the logistics API for integration testing."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Startup DB Initialisation
@app.on_event("startup")
async def startup():
    logger.info("Initializing mock logistics tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Mock logistics tables verified.")

# Bearer token helper
async def get_current_driver(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session)
) -> MockDriver:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer requerido."
        )
    token = authorization.split(" ")[1]
    
    # Query database for driver with this token
    stmt = select(MockDriver).where(MockDriver.token == token)
    res = await db.execute(stmt)
    driver = res.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado."
        )
    return driver

# -----------------
# Auth Endpoints
# -----------------
@app.post("/api/v1/auth/login")
async def login(payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db_session)):
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Faltan credenciales (email y password).")
    
    stmt = select(MockDriver).where(MockDriver.email == email)
    res = await db.execute(stmt)
    driver = res.scalar_one_or_none()
    
    if not driver or driver.password != password:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")
        
    # Generate mock token
    import secrets
    mock_token = f"mock-jwt-token-{secrets.token_hex(16)}"
    driver.token = mock_token
    await db.commit()
    
    return {
        "success": True,
        "token": mock_token,
        "user": {
            "email": driver.email,
            "name": driver.name
        }
    }

@app.post("/api/v1/auth/logout")
async def logout(driver: MockDriver = Depends(get_current_driver), db: AsyncSession = Depends(get_db_session)):
    driver.token = None
    await db.commit()
    return {"success": True, "message": "Sesión cerrada."}

@app.get("/api/v1/auth/me")
async def me(driver: MockDriver = Depends(get_current_driver)):
    return {
        "success": True,
        "data": {
            "email": driver.email,
            "name": driver.name,
            "role": "driver"
        }
    }

# -----------------
# Driver Tickets
# -----------------
@app.get("/api/v1/driver/tickets")
async def get_tickets(
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockTicket).order_by(MockTicket.id.desc())
    res = await db.execute(stmt)
    tickets = res.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "status": t.status,
                "description": t.description,
                "occurred_at": t.occurred_at.isoformat() if t.occurred_at else None,
                "latitude": t.latitude,
                "longitude": t.longitude,
                "items": t.items,
                "customer_phone": t.customer_phone,
                "customer_identity": t.customer_identity,
                "order_number": t.order_number
            }
            for t in tickets
        ]
    }

@app.get("/api/v1/driver/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockTicket).where(MockTicket.id == ticket_id)
    res = await db.execute(stmt)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} no encontrado.")
    return {
        "success": True,
        "data": {
            "id": t.id,
            "status": t.status,
            "description": t.description,
            "occurred_at": t.occurred_at.isoformat() if t.occurred_at else None,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "items": t.items,
            "customer_phone": t.customer_phone,
            "customer_identity": t.customer_identity,
            "order_number": t.order_number
        }
    }

@app.post("/api/v1/driver/tickets/{ticket_id}/change-status")
async def change_ticket_status(
    ticket_id: int,
    payload: Dict[str, Any] = Body(...),
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockTicket).where(MockTicket.id == ticket_id)
    res = await db.execute(stmt)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")
    
    new_status = payload.get("status")
    description = payload.get("description", f"Estado cambiado a {new_status}")
    
    t.status = new_status
    event = MockTicketEvent(ticket_id=ticket_id, status=new_status, description=description)
    db.add(event)
    await db.commit()
    
    return {"success": True, "message": f"Estado del ticket actualizado a {new_status}."}

@app.post("/api/v1/driver/tickets/{ticket_id}/evidence")
async def upload_evidence(ticket_id: int, driver: MockDriver = Depends(get_current_driver)):
    return {"success": True, "message": "Evidencia guardada correctamente."}

@app.post("/api/v1/driver/tickets/{ticket_id}/novelties")
async def upload_novelty(ticket_id: int, driver: MockDriver = Depends(get_current_driver)):
    return {"success": True, "message": "Novedad registrada."}

# -----------------
# Driver Utils
# -----------------
@app.get("/api/v1/driver/notifications")
async def get_notifications(driver: MockDriver = Depends(get_current_driver)):
    return {
        "success": True,
        "data": [
            {
                "id": 1,
                "message": "Operación logística iniciada.",
                "read": False,
                "created_at": "2026-07-29T12:00:00Z"
            }
        ]
    }

@app.post("/api/v1/driver/notifications/{notification_id}/read")
async def read_notification(notification_id: int, driver: MockDriver = Depends(get_current_driver)):
    return {"success": True}

@app.get("/api/v1/driver/novelty-reasons")
async def get_novelty_reasons(driver: MockDriver = Depends(get_current_driver)):
    return {
        "success": True,
        "data": [
            {"id": 1, "reason": "Cliente ausente"},
            {"id": 2, "reason": "Dirección incorrecta"},
            {"id": 3, "reason": "Rechazo del producto"}
        ]
    }

@app.post("/api/v1/driver/location")
async def register_location(payload: Dict[str, Any] = Body(...), driver: MockDriver = Depends(get_current_driver)):
    logger.info(f"Driver location registered: {payload}")
    return {"success": True}

# -----------------
# Subzones
# -----------------
@app.get("/api/v1/subzones")
async def list_subzones(driver: MockDriver = Depends(get_current_driver)):
    return {"success": True, "data": []}

# -----------------
# Logistic Operations
# -----------------
@app.get("/api/v1/logistic-operations")
async def get_operations(
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockLogisticOperation).order_by(MockLogisticOperation.id.desc())
    res = await db.execute(stmt)
    ops = res.scalars().all()
    
    result = []
    for op in ops:
        # Load stops
        stops_stmt = select(MockStop).where(MockStop.operation_id == op.id)
        stops_res = await db.execute(stops_stmt)
        stops = stops_res.scalars().all()
        result.append({
            "id": op.id,
            "status": op.status,
            "route": op.route,
            "driver_name": op.driver_name,
            "vehicle": op.vehicle,
            "stops": [
                {
                    "id": s.id,
                    "stop_name": s.stop_name,
                    "status": s.status,
                    "arrived_at": s.arrived_at.isoformat() if s.arrived_at else None,
                    "finished_at": s.finished_at.isoformat() if s.finished_at else None
                }
                for s in stops
            ]
        })
    return {"success": True, "data": result}

@app.get("/api/v1/logistic-operations/{id}")
async def get_operation_by_id(
    id: int,
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockLogisticOperation).where(MockLogisticOperation.id == id)
    res = await db.execute(stmt)
    op = res.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operación logística no encontrada.")
        
    stops_stmt = select(MockStop).where(MockStop.operation_id == op.id)
    stops_res = await db.execute(stops_stmt)
    stops = stops_res.scalars().all()
    
    return {
        "success": True,
        "data": {
            "id": op.id,
            "status": op.status,
            "route": op.route,
            "driver_name": op.driver_name,
            "vehicle": op.vehicle,
            "stops": [
                {
                    "id": s.id,
                    "stop_name": s.stop_name,
                    "status": s.status,
                    "arrived_at": s.arrived_at.isoformat() if s.arrived_at else None,
                    "finished_at": s.finished_at.isoformat() if s.finished_at else None
                }
                for s in stops
            ]
        }
    }

@app.post("/api/v1/logistic-operations/{id}/transition")
async def transition_operation(
    id: int,
    payload: Dict[str, Any] = Body(...),
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockLogisticOperation).where(MockLogisticOperation.id == id)
    res = await db.execute(stmt)
    op = res.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada.")
    
    transition = payload.get("transition")
    op.status = transition
    await db.commit()
    
    return {"success": True, "message": f"Transición {transition} realizada con éxito."}

@app.post("/api/v1/logistic-operations/{id}/incidents")
async def add_incident(
    id: int,
    payload: Dict[str, Any] = Body(...),
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockLogisticOperation).where(MockLogisticOperation.id == id)
    res = await db.execute(stmt)
    op = res.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada.")
        
    incident = MockIncident(
        operation_id=id,
        incident_type=payload.get("incident_type"),
        description=payload.get("description")
    )
    db.add(incident)
    await db.commit()
    
    return {"success": True, "message": "Incidente registrado."}

@app.post("/api/v1/logistic-operations/{id}/stops/{stop_id}/finish")
async def finish_stop(
    id: int,
    stop_id: int,
    driver: MockDriver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(MockStop).where(MockStop.operation_id == id, MockStop.id == stop_id)
    res = await db.execute(stmt)
    stop = res.scalar_one_or_none()
    if not stop:
        raise HTTPException(status_code=404, detail="Parada no encontrada.")
        
    import datetime
    stop.status = "finished"
    stop.finished_at = datetime.datetime.utcnow()
    await db.commit()
    
    return {"success": True, "message": "Parada finalizada."}

# -----------------
# Seed API (Reset and populate data)
# -----------------
@app.post("/api/v1/seed")
async def seed_data(db: AsyncSession = Depends(get_db_session)):
    # 1. Clean existing mock data
    logger.info("Cleaning mock logistics database tables...")
    await db.execute(update(MockDriver).values(token=None))
    await db.execute(delete(MockDriver))
    await db.execute(delete(MockStop))
    await db.execute(delete(MockIncident))
    await db.execute(delete(MockLogisticOperation))
    await db.execute(delete(MockTicketEvent))
    await db.execute(delete(MockTicket))
    await db.commit()

    # 2. Add drivers
    driver1 = MockDriver(
        email="gbailey@example.net",
        password="|]|{+-",
        name="Gloria Bailey",
        token=None
    )
    driver2 = MockDriver(
        email="admin@ferreteria.com",
        password="admin_pass",
        name="Administrador Ferretería",
        token=None
    )
    db.add_all([driver1, driver2])

    # 3. Add tickets
    t1 = MockTicket(
        id=1,
        status="created",
        description="Entrega de cemento y herramientas en obra",
        latitude=-0.180653,
        longitude=-78.467834,
        items=["5x Cemento Selvalegre", "1x Pala", "2x Carretilla"],
        customer_phone="593987654321",
        customer_identity="1723456789",
        order_number="PED-1001"
    )
    t2 = MockTicket(
        id=2,
        status="picking",
        description="Retiro de mercadería devuelta",
        latitude=-0.220123,
        longitude=-78.512345,
        items=["1x Martillo Eléctrico", "3x Cascos de seguridad"],
        customer_phone="593999888777",
        customer_identity="1700998877",
        order_number="PED-1002"
    )
    t3 = MockTicket(
        id=12345,
        status="in_route",
        description="Entrega a domicilio urgente",
        latitude=-0.190653,
        longitude=-78.477834,
        items=["2x Pintura Látex Suprema", "3x Brochas 3pulg"],
        customer_phone="593988888888",
        customer_identity="1711223344",
        order_number="PED-12345"
    )
    db.add_all([t1, t2, t3])
    await db.commit()

    # 4. Add logistic operations & stops
    op = MockLogisticOperation(
        id=100,
        status="in_progress",
        route="Ruta Centro-Norte",
        driver_name="Gloria Bailey",
        vehicle="Camión Hino GD-102"
    )
    db.add(op)
    await db.commit()

    s1 = MockStop(id=1, operation_id=100, stop_name="Sucursal Norte", status="finished")
    s2 = MockStop(id=2, operation_id=100, stop_name="Obra Eloy Alfaro", status="active")
    db.add_all([s1, s2])
    await db.commit()

    logger.info("Mock logistics database seeded successfully.")
    return {"success": True, "message": "Datos de prueba logísticos cargados correctamente."}

# Endpoint helper for healthcheck
@app.get("/health")
async def health():
    return {"status": "ok"}
