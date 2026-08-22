import logging
import httpx
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("chatbot-api.services.flowise")

class FlowiseService:
    def __init__(self):
        self.base_url = settings.FLOWISE_BASE_URL.rstrip('/')
        self.chatflow_id = settings.FLOWISE_CHATFLOW_ID
        self.api_key = settings.FLOWISE_API_KEY

    async def get_prediction(self, question: str, session_id: str, phone: str = "") -> str:
        """Sends the question to Flowise Prediction API and returns the text response."""
        if not self.chatflow_id:
            logger.error("FLOWISE_CHATFLOW_ID is not configured in environment.")
            return "Error: Flowise no está configurado."
            
        url = f"{self.base_url}/api/v1/prediction/{self.chatflow_id}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "question": question,
            "overrideConfig": {
                "sessionId": session_id,
                "vars": {
                    "user_phone": phone or "",
                    "session_id": session_id
                }
            }
        }
        
        logger.info(f"Sending message to Flowise (Session: {session_id})")
        logger.debug(f"Flowise payload: {payload}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=120.0  # Flowise might take a while to run LLMs and tools
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # The response can be a string, or a dict containing 'text' or 'json'
                    if isinstance(data, dict):
                        return data.get("text", str(data))
                    return str(data)
                
                logger.error(f"Flowise returned error status: {response.status_code} - {response.text}")
                return "No fue posible acceder a la información desde esta sesión. Puedes intentar nuevamente."
                
        except httpx.RequestError as e:
            logger.error(f"Network error calling Flowise: {str(e)}")
            return "No pude consultar esa información en este momento. Puedes intentar nuevamente o comunicarte con un asesor."
        except Exception as e:
            logger.error(f"Unexpected error in Flowise prediction: {str(e)}")
            return "Ocurrió un error inesperado al procesar tu solicitud."
