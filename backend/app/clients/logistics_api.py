import logging
import httpx
from typing import Optional, Dict, Any, List, Union
from app.config import settings

logger = logging.getLogger("chatbot-api.clients.logistics")

class LogisticsApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, code: str = "LOGISTICS_API_ERROR"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code

class LogisticsApiClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.LOGISTICS_API_BASE_URL
        self.timeout = float(settings.LOGISTICS_API_TIMEOUT_SECONDS)

    async def _request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Generic requester that appends bearer tokens and standard headers."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        
        req_headers = {
            "Accept": "application/json"
        }
        if token:
            req_headers["Authorization"] = f"Bearer {token}"
        if headers:
            req_headers.update(headers)
            
        logger.debug(f"Request: {method} {url} Headers: {req_headers} Payload: {json or data}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    json=json,
                    data=data,
                    files=files,
                    timeout=self.timeout
                )
                
                # Check for 401
                if response.status_code == 401:
                    logger.warning("Logistics API returned 401 Unauthenticated.")
                    raise LogisticsApiError("Unauthorized", status_code=401, code="UNAUTHENTICATED")
                    
                response.raise_for_status()
                
                # Check response format
                if "application/json" in response.headers.get("Content-Type", ""):
                    return response.json()
                else:
                    return {"raw_text": response.text}
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error from Logistics API: {e.response.status_code} - {e.response.text}")
            raise LogisticsApiError(
                message=f"Error en API logística: {e.response.text}",
                status_code=e.response.status_code,
                code="HTTP_STATUS_ERROR"
            )
        except httpx.RequestError as e:
            logger.error(f"Network error connecting to Logistics API: {str(e)}")
            raise LogisticsApiError(
                message="No fue posible conectar con la API logística.",
                status_code=None,
                code="LOGISTICS_API_UNAVAILABLE"
            )

    # -----------------
    # Auth Endpoints
    # -----------------
    async def login(self, email: str, password: str, device_name: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path="/api/v1/auth/login",
            json={"email": email, "password": password, "device_name": device_name}
        )

    async def logout(self, token: str) -> Dict[str, Any]:
        return await self._request(method="POST", path="/api/v1/auth/logout", token=token)

    async def get_me(self, token: str) -> Dict[str, Any]:
        return await self._request(method="GET", path="/api/v1/auth/me", token=token)

    # -----------------
    # Tickets
    # -----------------
    async def get_tickets(self, token: str) -> Union[Dict[str, Any], List[Any]]:
        return await self._request(method="GET", path="/api/v1/driver/tickets", token=token)

    async def get_ticket_by_id(self, ticket_id: int, token: str) -> Dict[str, Any]:
        return await self._request(method="GET", path=f"/api/v1/driver/tickets/{ticket_id}", token=token)

    async def change_ticket_status(self, ticket_id: int, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/driver/tickets/{ticket_id}/change-status",
            json=payload,
            token=token
        )

    async def upload_evidence(self, ticket_id: int, data: Dict[str, Any], files: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/driver/tickets/{ticket_id}/evidence",
            data=data,
            files=files,
            token=token
        )

    async def upload_novelty(self, ticket_id: int, data: Dict[str, Any], files: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/driver/tickets/{ticket_id}/novelties",
            data=data,
            files=files,
            token=token
        )

    # -----------------
    # Driver Utils
    # -----------------
    async def get_notifications(self, token: str) -> Union[Dict[str, Any], List[Any]]:
        return await self._request(method="GET", path="/api/v1/driver/notifications", token=token)

    async def read_notification(self, notification_id: int, token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/driver/notifications/{notification_id}/read",
            token=token
        )

    async def get_novelty_reasons(self, token: str) -> Union[Dict[str, Any], List[Any]]:
        return await self._request(method="GET", path="/api/v1/driver/novelty-reasons", token=token)

    async def send_location(self, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path="/api/v1/driver/location",
            json=payload,
            token=token
        )

    # -----------------
    # Subzones
    # -----------------
    async def get_subzones(self, token: str) -> Union[Dict[str, Any], List[Any]]:
        return await self._request(method="GET", path="/api/v1/subzones", token=token)

    async def create_subzone(self, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(method="POST", path="/api/v1/subzones", json=payload, token=token)

    async def update_subzone(self, subzone_id: int, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="PUT",
            path=f"/api/v1/subzones/{subzone_id}",
            json=payload,
            token=token
        )

    async def delete_subzone(self, subzone_id: int, token: str) -> Dict[str, Any]:
        return await self._request(method="DELETE", path=f"/api/v1/subzones/{subzone_id}", token=token)

    # -----------------
    # Logistic Operations
    # -----------------
    async def get_logistic_operations(self, token: str) -> Union[Dict[str, Any], List[Any]]:
        return await self._request(method="GET", path="/api/v1/logistic-operations", token=token)

    async def get_logistic_operation_by_id(self, operation_id: int, token: str) -> Dict[str, Any]:
        return await self._request(
            method="GET",
            path=f"/api/v1/logistic-operations/{operation_id}",
            token=token
        )

    async def create_logistic_operation(self, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path="/api/v1/logistic-operations",
            json=payload,
            token=token
        )

    async def update_logistic_operation(self, operation_id: int, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="PUT",
            path=f"/api/v1/logistic-operations/{operation_id}",
            json=payload,
            token=token
        )

    async def transition_logistic_operation(self, operation_id: int, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/logistic-operations/{operation_id}/transition",
            json=payload,
            token=token
        )

    async def add_logistic_incident(self, operation_id: int, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/logistic-operations/{operation_id}/incidents",
            json=payload,
            token=token
        )

    async def upload_logistic_attachment(self, operation_id: int, data: Dict[str, Any], files: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/logistic-operations/{operation_id}/attachments",
            data=data,
            files=files,
            token=token
        )

    async def add_logistic_stop(self, operation_id: int, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/logistic-operations/{operation_id}/stops",
            json=payload,
            token=token
        )

    async def finish_logistic_stop(self, operation_id: int, stop_id: int, token: str) -> Dict[str, Any]:
        return await self._request(
            method="POST",
            path=f"/api/v1/logistic-operations/{operation_id}/stops/{stop_id}/finish",
            token=token
        )
