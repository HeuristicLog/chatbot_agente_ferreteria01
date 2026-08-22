from typing import Dict

# Ticket status translations
TICKET_STATUS_MAP: Dict[str, str] = {
    "created": "Ticket creado.",
    "sent_to_warehouse": "Pedido enviado a bodega.",
    "assigned_to_warehouse": "Pedido asignado a bodega.",
    "picking": "Productos en preparación.",
    "loading": "Productos cargándose en el vehículo.",
    "loaded": "Productos cargados.",
    "dispatched": "Pedido despachado.",
    "in_route": "Pedido en ruta.",
    "delivered": "Pedido entregado.",
    "delivery_failed": "No fue posible completar la entrega.",
    "returning": "Pedido en proceso de retorno.",
    "arrived_back": "Pedido devuelto al punto de origen.",
    "cancelled": "Pedido cancelado."
}

# Logistic transition translations
LOGISTIC_TRANSITION_MAP: Dict[str, str] = {
    "start_trip": "Viaje iniciado.",
    "arrive_plant": "Vehículo en planta.",
    "start_queue": "Vehículo esperando en fila.",
    "enter_plant": "Vehículo dentro de la planta.",
    "start_loading": "Carga iniciada.",
    "finish_loading": "Carga finalizada.",
    "start_return": "Retorno iniciado.",
    "arrive_origin": "Vehículo en el punto de origen.",
    "start_unloading": "Descarga iniciada.",
    "finish_unloading": "Descarga finalizada.",
    "cancel": "Operación cancelada."
}

# Incident type translations
INCIDENT_TYPE_MAP: Dict[str, str] = {
    "sleep_break": "Parada para descanso/sueño.",
    "food_break": "Parada para alimentación.",
    "plant_delay": "Demora en planta.",
    "queue_delay": "Demora en fila de espera.",
    "mechanical_issue": "Fallo mecánico del vehículo.",
    "document_issue": "Inconveniente con documentos.",
    "plant_no_dispatch": "Planta sin despacho.",
    "accident": "Accidente de tránsito.",
    "route_change": "Desvío o cambio de ruta.",
    "warehouse_closed": "Bodega/Destino cerrado.",
    "other": "Otro tipo de novedad o retraso."
}

def translate_ticket_status(status_code: str) -> str:
    """Translates a technical ticket status key into friendly Spanish text."""
    clean_code = str(status_code).strip().lower()
    return TICKET_STATUS_MAP.get(clean_code, f"Estado: {status_code}")

def translate_logistic_transition(transition_code: str) -> str:
    """Translates a logistic transition key into friendly Spanish text."""
    clean_code = str(transition_code).strip().lower()
    return LOGISTIC_TRANSITION_MAP.get(clean_code, f"Transición: {transition_code}")

def translate_incident_type(incident_code: str) -> str:
    """Translates an incident type key into friendly Spanish text."""
    clean_code = str(incident_code).strip().lower()
    return INCIDENT_TYPE_MAP.get(clean_code, f"Incidente: {incident_code}")
