import logging
from typing import List, Dict, Any, Union, Optional
from app.clients.logistics_api import LogisticsApiClient
from app.services.auth_service import LogisticsAuthService
from app.domain.models import NotificationSummary, NoveltyReason

logger = logging.getLogger("chatbot-api.services.notification")

class NotificationService:
    def __init__(self, auth_service: LogisticsAuthService, api_client: Optional[LogisticsApiClient] = None):
        self.auth = auth_service
        self.api = api_client or LogisticsApiClient()

    async def get_notifications(self) -> List[NotificationSummary]:
        """Fetches active notifications for the driver."""
        raw_result = await self.auth.execute_with_retry(self.api.get_notifications)
        
        items_raw = []
        if isinstance(raw_result, list):
            items_raw = raw_result
        elif isinstance(raw_result, dict):
            items_raw = raw_result.get("data", raw_result.get("notifications", []))
            if not isinstance(items_raw, list):
                items_raw = [items_raw]
                
        notifications = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            notifications.append(
                NotificationSummary(
                    id=item.get("id"),
                    message=item.get("message"),
                    read=item.get("read"),
                    created_at=item.get("created_at")
                )
            )
        return notifications

    async def read_notification(self, notification_id: int) -> Dict[str, Any]:
        """Marks a specific notification as read."""
        return await self.auth.execute_with_retry(self.api.read_notification, notification_id)

    async def get_novelty_reasons(self) -> List[NoveltyReason]:
        """Retrieves standard driver novelty reasons."""
        raw_result = await self.auth.execute_with_retry(self.api.get_novelty_reasons)
        
        items_raw = []
        if isinstance(raw_result, list):
            items_raw = raw_result
        elif isinstance(raw_result, dict):
            items_raw = raw_result.get("data", raw_result.get("reasons", []))
            if not isinstance(items_raw, list):
                items_raw = [items_raw]
                
        reasons = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            reasons.append(
                NoveltyReason(
                    id=item.get("id"),
                    reason=item.get("reason"),
                    description=item.get("description")
                )
            )
        return reasons

    async def send_location(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submits real-time driver coordinates to the logistics API."""
        return await self.auth.execute_with_retry(self.api.send_location, payload)
