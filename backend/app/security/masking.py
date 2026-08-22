import re
from typing import Any, Dict, List, Union

SENSITIVE_KEYS = {"password", "token", "access_token", "bearertoken", "key", "api_key", "secret", "authorization"}

def mask_sensitive_keys(data: Any) -> Any:
    """Recursively traverses dictionary/list structure to mask sensitive security keys."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                masked[k] = "[MASKED]"
            else:
                masked[k] = mask_sensitive_keys(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_keys(item) for item in data]
    elif isinstance(data, str):
        # Regex to mask bearer tokens inside strings
        pattern = r"(Bearer\s+)[a-zA-Z0-9_\-\.]+"
        return re.sub(pattern, r"\1[MASKED]", data)
    return data

def mask_driver_and_locations(data: Any) -> Any:
    """Recursively hides coordinates/locations and trims driver names to first names."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if k_lower in {"name", "driver_name", "nombre", "conductor"}:
                if isinstance(v, str) and v:
                    parts = v.strip().split()
                    if len(parts) > 1:
                        masked[k] = f"{parts[0]} [MASKED]"
                    else:
                        masked[k] = v
                else:
                    masked[k] = v
            elif k_lower in {"latitude", "longitude", "lat", "lon", "lng"}:
                masked[k] = None
            elif k_lower in {"address", "direccion", "origin", "destination", "origen", "destino"}:
                masked[k] = "[OCULTO por seguridad]"
            else:
                masked[k] = mask_driver_and_locations(v)
        return masked
    elif isinstance(data, list):
        return [mask_driver_and_locations(item) for item in data]
    return data
