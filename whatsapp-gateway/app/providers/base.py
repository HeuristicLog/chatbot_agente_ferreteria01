from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.models import IncomingMessage

class WhatsAppProvider(ABC):
    @abstractmethod
    async def parse_incoming_message(self, raw_payload: Dict[str, Any]) -> List[IncomingMessage]:
        """Parsea la peticion cruda del webhook y extrae los mensajes recibidos."""
        pass

    @abstractmethod
    async def send_text_message(self, to_phone: str, message: str, **kwargs) -> bool:
        """Envia un mensaje de texto plano."""
        pass

    @abstractmethod
    async def send_interactive_options(self, to_phone: str, message: str, options: List[str], **kwargs) -> bool:
        """Envia botones u opciones interactivas."""
        pass

    @abstractmethod
    async def send_cta_url_message(self, to_phone: str, body: str, display_text: str, url: str, header: str = "", footer: str = "", **kwargs) -> bool:
        """Envia un mensaje interactivo con boton CTA URL que abre la webview/navegador embebido."""
        pass

    @abstractmethod
    async def send_flow_message(self, to_phone: str, body: str, flow_id: str, flow_cta: str, flow_token: str = "token_01", screen: str = "CATALOG_SCREEN", header: str = "", footer: str = "", **kwargs) -> bool:
        """Envia un mensaje interactivo con WhatsApp Flow oficial de Meta (pantalla emergente nativa)."""
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """Marca un mensaje especifico como leido."""
        pass

    @abstractmethod
    async def download_media(self, media_id: str) -> Optional[bytes]:
        """Descarga un archivo multimedia adjunto."""
        pass
