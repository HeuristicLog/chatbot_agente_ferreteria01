import logging
from fastapi import APIRouter, Body, HTTPException, status
from typing import Dict, Any, List, Optional

logger = logging.getLogger("chatbot-api.api.logistics_mock")
router = APIRouter()

# Mock DB Data
DRIVERS = {
    "gbailey@example.net": {
        "email": "gbailey@example.net",
        "password": "|]|{+-",
        "name": "Gloria Bailey",
        "token": "mock-driver-token-abc"
    },
    "gbailley@example.net": {
        "email": "gbailey@example.net",
        "password": "|]|{+-",
        "name": "Gloria Bailey",
        "token": "mock-driver-token-abc"
    }
}

TICKETS = [
    {
        "id": 1,
        "status": "created",
        "description": "Entrega de cemento y herramientas en obra",
        "occurred_at": "2026-07-28T12:00:00Z",
        "latitude": -0.180653,
        "longitude": -78.467834,
        "items": ["5x Cemento Selvalegre", "1x Pala", "2x Carretilla"]
    },
    {
        "id": 2,
        "status": "picking",
        "description": "Retiro de mercadería devuelta",
        "occurred_at": "2026-07-28T14:30:00Z",
        "latitude": -0.220123,
        "longitude": -78.512345,
        "items": ["1x Martillo Eléctrico", "3x Cascos de seguridad"]
    }
]

NOTIFICATIONS = [
    {
        "id": 1,
        "message": "Alerta: Retraso en la ruta norte debido a tráfico intenso.",
        "read": False,
        "created_at": "2026-07-28T15:00:00Z"
    }
]

OPERATIONS = [
    {
        "id": 100,
        "status": "in_progress",
        "route": "Ruta Centro-Norte",
        "driver_name": "Gloria Bailey",
        "vehicle": "Camión Hino GD-102",
        "stops": ["Sucursal Norte", "Obra Eloy Alfaro"]
    }
]

# 1. Login
@router.post("/api/v1/auth/login")
async def mock_login(payload: Dict[str, Any] = Body(...)):
    logger.info(f"Mock login received payload: {payload}")
    email = payload.get("email")
    password = payload.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Faltan credenciales")
        
    driver = DRIVERS.get(email)
    if not driver or (driver["password"] != password and driver["password"] + "}" != password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
    logger.info(f"Driver logged in successfully: {email}")
    return {
        "success": True,
        "token": driver["token"],
        "user": {
            "email": driver["email"],
            "name": driver["name"]
        }
    }

# 2. Get Me
@router.get("/api/v1/auth/me")
async def mock_get_me():
    return {
        "success": True,
        "data": {
            "email": "gbailey@example.net",
            "name": "Gloria Bailey",
            "role": "driver"
        }
    }

# 3. Logout
@router.post("/api/v1/auth/logout")
async def mock_logout():
    return {"success": True}

# 4. Get Tickets
@router.get("/api/v1/driver/tickets")
async def mock_get_tickets():
    return {
        "success": True,
        "data": TICKETS
    }

# 5. Get Ticket By ID
@router.get("/api/v1/driver/tickets/{ticket_id}")
async def mock_get_ticket_by_id(ticket_id: int):
    ticket = next((t for t in TICKETS if t["id"] == ticket_id), None)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {
        "success": True,
        "data": ticket
    }

# 6. Change Ticket Status
@router.post("/api/v1/driver/tickets/{ticket_id}/change-status")
async def mock_change_status(ticket_id: int, payload: Dict[str, Any] = Body(...)):
    ticket = next((t for t in TICKETS if t["id"] == ticket_id), None)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket["status"] = payload.get("status", ticket["status"])
    return {"success": True, "message": "Estado actualizado"}

# 7. Upload Evidence
@router.post("/api/v1/driver/tickets/{ticket_id}/evidence")
async def mock_upload_evidence(ticket_id: int):
    return {"success": True, "message": "Evidencia guardada"}

# 8. Upload Novelty
@router.post("/api/v1/driver/tickets/{ticket_id}/novelties")
async def mock_upload_novelty(ticket_id: int):
    return {"success": True, "message": "Novedad guardada"}

# 9. Get Notifications
@router.get("/api/v1/driver/notifications")
async def mock_get_notifications():
    return {
        "success": True,
        "data": NOTIFICATIONS
    }

# 10. Read Notification
@router.post("/api/v1/driver/notifications/{notification_id}/read")
async def mock_read_notification(notification_id: int):
    notif = next((n for n in NOTIFICATIONS if n["id"] == notification_id), None)
    if notif:
        notif["read"] = True
    return {"success": True}

# 11. Novelty Reasons
@router.get("/api/v1/driver/novelty-reasons")
async def mock_novelty_reasons():
    return {
        "success": True,
        "data": [
            {"id": 1, "reason": "Cliente ausente"},
            {"id": 2, "reason": "Dirección incorrecta"}
        ]
    }

# 12. Send Location
@router.post("/api/v1/driver/location")
async def mock_send_location():
    return {"success": True}

# 13. Subzones
@router.get("/api/v1/subzones")
async def mock_subzones():
    return {"success": True, "data": []}

# 14. Logistic Operations
@router.get("/api/v1/logistic-operations")
async def mock_logistic_operations():
    return {
        "success": True,
        "data": OPERATIONS
    }

# 15. Logistic Operation by ID
@router.get("/api/v1/logistic-operations/{operation_id}")
async def mock_logistic_operation_by_id(operation_id: int):
    op = next((o for o in OPERATIONS if o["id"] == operation_id), None)
    if not op:
        raise HTTPException(status_code=404, detail="Operación no encontrada")
    return {
        "success": True,
        "data": op
    }
