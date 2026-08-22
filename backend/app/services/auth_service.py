import logging
import redis.asyncio as redis
from typing import Optional, Dict, Any
from app.config import settings
from app.clients.logistics_api import LogisticsApiClient, LogisticsApiError

logger = logging.getLogger("chatbot-api.services.auth")

class LogisticsAuthService:
    TOKEN_CACHE_KEY = "logistics_api_token"
    
    def __init__(self, redis_client: redis.Redis, api_client: Optional[LogisticsApiClient] = None, custom_token: Optional[str] = None):
        self.redis = redis_client
        self.api = api_client or LogisticsApiClient()
        self.custom_token = custom_token

    async def login(self) -> str:
        """Executes a POST request to login technical account and caches the token."""
        logger.info(f"Attempting technical login for: {settings.LOGISTICS_API_EMAIL}")
        if not settings.LOGISTICS_API_EMAIL or not settings.LOGISTICS_API_PASSWORD:
            raise LogisticsApiError("Las credenciales de API Logística (LOGISTICS_API_EMAIL/PASSWORD) no están configuradas.")
            
        try:
            result = await self.api.login(
                email=settings.LOGISTICS_API_EMAIL,
                password=settings.LOGISTICS_API_PASSWORD,
                device_name=settings.LOGISTICS_API_DEVICE_NAME
            )
            
            # The token is usually returned in data or token field. Let's inspect potential keys
            # or check standard patterns: {"token": "xyz", "user": {}} or {"data": {"token": "xyz"}}
            token = None
            if "token" in result:
                token = result["token"]
            elif "data" in result and isinstance(result["data"], dict) and "token" in result["data"]:
                token = result["data"]["token"]
            elif "token" in result.get("data", {}):
                token = result["data"]["token"]
                
            if not token:
                # If structure is different, fallback to entire string or key search
                for key in ["token", "access_token", "jwt"]:
                    if key in result:
                        token = result[key]
                        break
                        
            if not token:
                logger.error(f"Structure returned by login API lacks a token: {result}")
                raise LogisticsApiError("La respuesta de login de la API logística no contiene un token válido.")
                
            # Cache the token in Redis with a 2-hour TTL (or safe threshold)
            await self.redis.set(self.TOKEN_CACHE_KEY, token, ex=7200)
            logger.info("Technical token cached in Redis successfully.")
            return token
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    async def get_valid_token(self) -> str:
        """Retrieves active cached token or triggers a new login flow."""
        if self.custom_token:
            return self.custom_token
        token = await self.redis.get(self.TOKEN_CACHE_KEY)
        if token:
            logger.debug("Active token retrieved from Redis cache.")
            return token
            
        logger.info("No active token found in cache. Performing new login.")
        return await self.login()

    async def invalidate_token(self) -> None:
        """Removes the technical token from Redis cache (e.g. after a 401)."""
        logger.warning("Invalidating cached logistics token.")
        await self.redis.delete(self.TOKEN_CACHE_KEY)

    async def logout(self) -> None:
        """Cleans up logistics API session and clears cache."""
        token = await self.redis.get(self.TOKEN_CACHE_KEY)
        if token:
            try:
                await self.api.logout(token)
            except Exception as e:
                logger.warning(f"Error calling logout endpoint: {str(e)}")
            await self.invalidate_token()
            logger.info("Successfully logged out technical session.")

    async def build_auth_headers(self) -> Dict[str, str]:
        """Utility to retrieve a valid token and format standard Authorization headers."""
        token = await self.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    async def execute_with_retry(self, api_func, *args, **kwargs) -> Any:
        """Helper to run API operations, refreshing token and re-trying once in case of a 401."""
        token = await self.get_valid_token()
        try:
            return await api_func(*args, token=token, **kwargs)
        except LogisticsApiError as e:
            if e.status_code == 401:
                logger.warning("Session expired (401). Re-authenticating and retrying.")
                await self.invalidate_token()
                # Retry once with a new token
                new_token = await self.get_valid_token()
                return await api_func(*args, token=new_token, **kwargs)
            raise
