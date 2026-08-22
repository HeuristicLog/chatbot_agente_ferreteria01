import secrets
from app.config import settings

def compare_internal_api_key(provided_key: str) -> bool:
    """Performs a constant-time comparison of the shared internal API key."""
    if not provided_key:
        return False
    return secrets.compare_digest(provided_key, settings.INTERNAL_API_KEY)
