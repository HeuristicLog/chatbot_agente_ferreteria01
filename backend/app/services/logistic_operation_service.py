import logging
from typing import List, Dict, Any, Optional

from app.clients.logistics_api import LogisticsApiClient
from app.services.auth_service import LogisticsAuthService
from app.services.ticket_service import resolve_file_param
from app.domain.status_translator import translate_logistic_transition
from app.domain.models import LogisticOperationSummary, LogisticOperationDetail

logger = logging.getLogger("chatbot-api.services.logistic_operation")

class LogisticOperationService:
    def __init__(self, auth_service: LogisticsAuthService, api_client: Optional[LogisticsApiClient] = None):
        self.auth = auth_service
        self.api = api_client or LogisticsApiClient()

    async def get_operations(self) -> List[LogisticOperationSummary]:
        """Fetches active logistic operations, translating status keys to Spanish."""
        raw_result = await self.auth.execute_with_retry(self.api.get_logistic_operations)
        
        items_raw = []
        if isinstance(raw_result, list):
            items_raw = raw_result
        elif isinstance(raw_result, dict):
            items_raw = raw_result.get("data", raw_result.get("operations", []))
            if not isinstance(items_raw, list):
                items_raw = [items_raw]
                
        operations = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            status_code = item.get("status", "pending")
            operations.append(
                LogisticOperationSummary(
                    id=item.get("id"),
                    origin=item.get("origin", ""),
                    destination=item.get("destination", ""),
                    status=status_code,
                    status_display=translate_logistic_transition(status_code)
                )
            )
        return operations

    async def get_operation_by_id(self, operation_id: int) -> Optional[LogisticOperationDetail]:
        """Fetches a specific operation details, applying state translations."""
        try:
            raw_result = await self.auth.execute_with_retry(self.api.get_logistic_operation_by_id, operation_id)
        except Exception as e:
            logger.warning(f"Operation {operation_id} not found: {str(e)}")
            return None
            
        item = {}
        if isinstance(raw_result, dict):
            item = raw_result.get("data", raw_result)
            
        status_code = item.get("status", "pending")
        return LogisticOperationDetail(
            id=item.get("id", operation_id),
            origin=item.get("origin", ""),
            destination=item.get("destination", ""),
            status=status_code,
            status_display=translate_logistic_transition(status_code),
            driver_id=item.get("driver_id"),
            vehicle_id=item.get("vehicle_id"),
            notes=item.get("notes"),
            scheduled_start_at=item.get("scheduled_start_at"),
            scheduled_arrival_at=item.get("scheduled_arrival_at"),
            raw_payload=item
        )

    async def create_operation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submits a new logistic operation to the logistics API."""
        return await self.auth.execute_with_retry(self.api.create_logistic_operation, payload)

    async def update_operation(self, operation_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Modifies details of an existing operation."""
        return await self.auth.execute_with_retry(self.api.update_logistic_operation, operation_id, payload)

    async def transition_operation(self, operation_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a state transition for the logistic operation."""
        return await self.auth.execute_with_retry(self.api.transition_logistic_operation, operation_id, payload)

    async def add_incident(self, operation_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Registers a transit incident on the operation."""
        return await self.auth.execute_with_retry(self.api.add_logistic_incident, operation_id, payload)

    async def upload_attachment(self, operation_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves file attachments and uploads them as multipart data to the logistics API."""
        file_data = form_data.pop("file_data", None)
        file_name = form_data.pop("file_name", "document")
        
        files = {}
        if file_data:
            resolved_file = await resolve_file_param(file_data, file_name)
            if resolved_file:
                files["file"] = resolved_file
                
        return await self.auth.execute_with_retry(
            self.api.upload_logistic_attachment,
            operation_id,
            data=form_data,
            files=files
        )

    async def add_stop(self, operation_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Registers a new intermediate stop in the route."""
        return await self.auth.execute_with_retry(self.api.add_logistic_stop, operation_id, payload)

    async def finish_stop(self, operation_id: int, stop_id: int) -> Dict[str, Any]:
        """Concludes an intermediate route stop."""
        return await self.auth.execute_with_retry(self.api.finish_logistic_stop, operation_id, stop_id)
