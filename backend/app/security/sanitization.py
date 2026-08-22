import re

# Prompt Injection mitigation: Block messages trying to access system prompts or instructions
PROMPT_INJECTION_KEYWORDS = [
    "revelar el prompt", "reveal prompt", "ignora las instrucciones", "ignore instructions",
    "reglas del sistema", "system rules", "nueva instruccion", "new instruction",
    "eres ahora", "you are now", "actúa como", "act as", "override rules"
]

def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """Sanitizes text messages, stripping potential danger vectors and enforcing length constraints."""
    if not text:
        return ""
    
    # 1. Truncate length
    sanitized = text[:max_length]
    
    # 2. Check for potential prompt injection attempts and strip critical keywords
    text_lower = sanitized.lower()
    for kw in PROMPT_INJECTION_KEYWORDS:
        if kw in text_lower:
            # Replace injection phrases with a neutral marker
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            sanitized = pattern.sub("[REDACTED INJECTION ATTEMPT]", sanitized)
            
    # 3. Strip HTML tags
    sanitized = re.sub(r"<[^>]*>", "", sanitized)
    
    return sanitized.strip()
