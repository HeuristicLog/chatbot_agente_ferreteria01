import base64
import re
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.clients.logistics_api import LogisticsApiClient
from app.services.auth_service import LogisticsAuthService
from app.domain.status_translator import translate_ticket_status
from app.domain.models import TicketSummary, TicketDetail

logger = logging.getLogger("chatbot-api.services.ticket")

async def resolve_file_param(file_data: str, field_name: str) -> Optional[tuple]:
    """Helper to convert a base64 string or an external URL into a binary file tuple (filename, bytes, content_type) for multipart uploading."""
    if not file_data:
        return None
    try:
        if file_data.startswith("http://") or file_data.startswith("https://"):
            logger.debug(f"Downloading file from URL: {file_data}")
            async with httpx.AsyncClient() as client:
                resp = await client.get(file_data, timeout=15.0)
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                    ext = content_type.split("/")[-1] if "/" in content_type else "jpg"
                    return (f"{field_name}.{ext}", resp.content, content_type)
        else:
            # Base64 parsing
            logger.debug("Decoding base64 file data")
            # Strip data URI header if present
            base64_clean = re.sub(r'^data:[a-zA-Z0-9/\+]+;base64,', '', file_data)
            binary_data = base64.b64decode(base64_clean)
            # Basic mime type guess (defaulting to jpeg)
            return (f"{field_name}.jpg", binary_data, "image/jpeg")
    except Exception as e:
        logger.warning(f"Error resolving file parameter {field_name}: {str(e)}")
    return None

class TicketService:
    def __init__(self, auth_service: LogisticsAuthService, api_client: Optional[LogisticsApiClient] = None):
        self.auth = auth_service
        self.api = api_client or LogisticsApiClient()

    async def get_tickets(self) -> List[TicketSummary]:
        """Retrieves and translates the driver's active tickets."""
        raw_result = await self.auth.execute_with_retry(self.api.get_tickets)
        
        # API can return a list directly, or wrap it in a data key
        tickets_raw = []
        if isinstance(raw_result, list):
            tickets_raw = raw_result
        elif isinstance(raw_result, dict):
            tickets_raw = raw_result.get("data", raw_result.get("tickets", []))
            if not isinstance(tickets_raw, list):
                tickets_raw = [tickets_raw] # Single record wrapped
                
        tickets = []
        for t in tickets_raw:
            if not isinstance(t, dict):
                continue
            status_code = t.get("status", "created")
            tickets.append(
                TicketSummary(
                    id=t.get("id"),
                    status=status_code,
                    status_display=translate_ticket_status(status_code),
                    occurred_at=t.get("occurred_at")
                )
            )
        return tickets

    async def get_ticket_by_id(self, ticket_id: int) -> Optional[TicketDetail]:
        """Retrieves detailed information of a specific ticket, returning Spanish translation."""
        try:
            raw_result = await self.auth.execute_with_retry(self.api.get_ticket_by_id, ticket_id)
        except Exception as e:
            logger.warning(f"Ticket {ticket_id} not found: {str(e)}")
            return None
            
        t = {}
        if isinstance(raw_result, dict):
            t = raw_result.get("data", raw_result)
            
        status_code = t.get("status", "created")
        return TicketDetail(
            id=t.get("id", ticket_id),
            status=status_code,
            status_display=translate_ticket_status(status_code),
            description=t.get("description"),
            occurred_at=t.get("occurred_at"),
            latitude=t.get("latitude"),
            longitude=t.get("longitude"),
            raw_payload=t
        )

    async def change_ticket_status(self, ticket_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submits a ticket status change event to the logistics API."""
        return await self.auth.execute_with_retry(self.api.change_ticket_status, ticket_id, payload)

    async def upload_evidence(self, ticket_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parses and submits delivery evidence files (signature, photos) to the logistics API."""
        # 1. Extract file paths/URLs/base64 from form data
        photo_str = form_data.pop("photo", None)
        signature_str = form_data.pop("signature", None)
        photos_str_list = form_data.pop("photos", None) # list or JSON string of list
        
        files = {}
        
        # Resolve photo
        if photo_str:
            photo_file = await resolve_file_param(photo_str, "photo")
            if photo_file:
                files["photo"] = photo_file
                
        # Resolve signature
        if signature_str:
            sig_file = await resolve_file_param(signature_str, "signature")
            if sig_file:
                files["signature"] = sig_file
                
        # Resolve list of additional photos
        if photos_str_list:
            if isinstance(photos_str_list, str):
                # Try parsing as JSON array
                try:
                    import json
                    photos_str_list = json.loads(photos_str_list)
                except Exception:
                    photos_str_list = [photos_str_list]
                    
            if isinstance(photos_str_list, list):
                for idx, p_str in enumerate(photos_str_list):
                    p_file = await resolve_file_param(p_str, f"photo_{idx}")
                    if p_file:
                        files[f"photos[{idx}]"] = p_file

        return await self.auth.execute_with_retry(
            self.api.upload_evidence,
            ticket_id,
            data=form_data,
            files=files
        )

    async def upload_novelty(self, ticket_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parses and submits ticket novelty logs and photos to the logistics API."""
        photo_str = form_data.pop("photo", None)
        photos_str_list = form_data.pop("photos", None)
        
        files = {}
        if photo_str:
            photo_file = await resolve_file_param(photo_str, "photo")
            if photo_file:
                files["photo"] = photo_file
                
        if photos_str_list:
            if isinstance(photos_str_list, str):
                try:
                    import json
                    photos_str_list = json.loads(photos_str_list)
                except Exception:
                    photos_str_list = [photos_str_list]
            if isinstance(photos_str_list, list):
                for idx, p_str in enumerate(photos_str_list):
                    p_file = await resolve_file_param(p_str, f"photo_{idx}")
                    if p_file:
                        files[f"photos[{idx}]"] = p_file

        return await self.auth.execute_with_retry(
            self.api.upload_novelty,
            ticket_id,
            data=form_data,
            files=files
        )
