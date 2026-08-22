from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# -----------------
# Standard Envelope Response
# -----------------

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Codigo tecnico del error")
    retryable: bool = Field(False, description="Indica si la operacion puede reintentarse")

    class Config:
        extra = "allow"

class StandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si la operacion fue exitosa")
    data: Optional[Any] = Field(None, description="Datos de la respuesta")
    message: str = Field(..., description="Mensaje explicativo para el usuario")
    error: Optional[ErrorDetail] = Field(None, description="Detalles del error en caso de fallo")
    request_id: str = Field(..., description="ID unico de transaccion para rastreo")

    class Config:
        extra = "allow"

# -----------------
# Domain Models (Logistics API Mapping)
# -----------------

class TicketSummary(BaseModel):
    id: int = Field(..., description="ID del ticket")
    status: str = Field(..., description="Codigo del estado")
    status_display: Optional[str] = Field(None, description="Estado traducido al espanol")
    occurred_at: Optional[str] = Field(None, description="Ultima actualizacion")

    class Config:
        extra = "allow"

class TicketDetail(BaseModel):
    id: int = Field(..., description="ID del ticket")
    status: str = Field(..., description="Codigo del estado")
    status_display: Optional[str] = Field(None, description="Estado traducido al espanol")
    description: Optional[str] = Field(None, description="Descripcion del ticket")
    occurred_at: Optional[str] = Field(None, description="Fecha de creacion o evento")
    latitude: Optional[float] = Field(None)
    longitude: Optional[float] = Field(None)
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Payload original para procesamiento interno")

    class Config:
        extra = "allow"

class NotificationSummary(BaseModel):
    id: int = Field(..., description="ID de la notificacion")
    message: Optional[str] = Field(None, description="Contenido de la notificacion")
    read: Optional[bool] = Field(None, description="Si fue leida")
    created_at: Optional[str] = Field(None)

    class Config:
        extra = "allow"

class NoveltyReason(BaseModel):
    id: int = Field(..., description="ID del motivo")
    reason: str = Field(..., description="Motivo de la novedad")
    description: Optional[str] = Field(None)

    class Config:
        extra = "allow"

class LogisticOperationSummary(BaseModel):
    id: int = Field(..., description="ID de la operacion")
    origin: str = Field(..., description="Origen")
    destination: str = Field(..., description="Destino")
    status: Optional[str] = Field(None)
    status_display: Optional[str] = Field(None)

    class Config:
        extra = "allow"

class LogisticOperationDetail(BaseModel):
    id: int = Field(..., description="ID de la operacion")
    origin: str = Field(..., description="Origen")
    destination: str = Field(..., description="Destino")
    status: Optional[str] = Field(None)
    status_display: Optional[str] = Field(None)
    driver_id: Optional[int] = Field(None)
    vehicle_id: Optional[int] = Field(None)
    notes: Optional[str] = Field(None)
    scheduled_start_at: Optional[str] = Field(None)
    scheduled_arrival_at: Optional[str] = Field(None)
    raw_payload: Optional[Dict[str, Any]] = Field(None)

    class Config:
        extra = "allow"

# -----------------
# FAQ and Handoff Requests
# -----------------

class FAQSearchRequest(BaseModel):
    query: str = Field(..., description="Pregunta a buscar")
    limit: int = Field(5, description="Cantidad maxima de resultados")

class FAQSearchResult(BaseModel):
    text: str = Field(..., description="Texto relevante del documento")
    source: str = Field(..., description="Nombre del archivo fuente")
    category: str = Field(..., description="Categoria del documento")
    score: float = Field(..., description="Puntaje de similitud")

    class Config:
        extra = "allow"

class HandoffRequest(BaseModel):
    session_id: str = Field(..., description="ID de sesion unico")
    phone: str = Field(..., description="Numero del usuario de WhatsApp")
    reason: Optional[str] = Field(None, description="Razon de la transferencia")
    summary: Optional[str] = Field(None, description="Resumen de la conversacion")
    ticket_id: Optional[int] = Field(None)
    operation_id: Optional[int] = Field(None)
    sucursal: Optional[str] = Field(None, description="Sucursal de la cual se requiere atencion")
    phone_number_id: Optional[str] = Field(None, description="Meta phone number ID")

# -----------------
# Internal/Gateway Message Passing
# -----------------

class IncomingWhatsAppMessage(BaseModel):
    phone: str
    message: str
    message_id: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OutgoingWhatsAppMessage(BaseModel):
    phone: str
    message: str
    interactive_options: Optional[List[str]] = None
    media_url: Optional[str] = None

class ConversationSession(BaseModel):
    session_id: str
    phone_hash: str
    last_query_type: Optional[str] = None
    selected_ticket_id: Optional[int] = None
    selected_operation_id: Optional[int] = None
    handoff_requested: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"

class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = Field("INFO")
    request_id: str
    session_id: str
    event: str
    tool: Optional[str] = None
    success: bool = True
    duration_ms: int = 0
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
