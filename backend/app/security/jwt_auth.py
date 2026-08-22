import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Dict, Any
from app.config import settings

SECRET_KEY = settings.INTERNAL_API_KEY or "jwt_secret_key_change_me"

def hash_password(password: str) -> str:
    """Hashes password using PBKDF2-HMAC-SHA256 (standard library)."""
    salt = hashlib.sha256(SECRET_KEY.encode()).digest()
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return base64.b64encode(key).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against its PBKDF2 hash."""
    return hash_password(plain_password) == hashed_password

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_jwt_token(data: dict, expires_in_seconds: int = 3600) -> str:
    """Generates a standard HS256 JWT token using Python standard library."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in_seconds
    
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    
    msg = f"{base64url_encode(header_json)}.{base64url_encode(payload_json)}"
    
    sig = hmac.new(SECRET_KEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).digest()
    return f"{msg}.{base64url_encode(sig)}"

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates an HS256 JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        msg = f"{parts[0]}.{parts[1]}"
        sig_check = hmac.new(SECRET_KEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).digest()
        
        if not hmac.compare_digest(base64url_decode(parts[2]), sig_check):
            return None
            
        payload = json.loads(base64url_decode(parts[1]).decode('utf-8'))
        
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None
