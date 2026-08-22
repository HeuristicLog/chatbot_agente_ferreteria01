from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class IncomingMessage(BaseModel):
    phone: str = Field(..., description="Numero del remitente (ej: 593999999999)")
    message: str = Field(..., description="Contenido de texto del mensaje")
    message_id: Optional[str] = Field(None, description="ID unico del mensaje externo")
    media_url: Optional[str] = Field(None, description="URL del archivo multimedia si existe")
    media_type: Optional[str] = Field(None, description="Tipo MIME del archivo multimedia")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata adicional")

class OutgoingMessage(BaseModel):
    phone: str = Field(..., description="Numero del destinatario")
    message: str = Field(..., description="Contenido del mensaje de texto")
    interactive_options: Optional[List[str]] = Field(None, description="Opciones interactivas/botones si aplica")
    media_url: Optional[str] = Field(None, description="URL de adjunto si aplica")
    phone_number_id: Optional[str] = Field(None, description="Meta phone number ID")
    access_token: Optional[str] = Field(None, description="Meta access token")
