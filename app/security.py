import hmac
from fastapi import Request
from .config import USERNAME, PASSWORD, STAFF_ENABLED

def credentials_valid(username: str, password: str) -> bool:
    if not STAFF_ENABLED or PASSWORD is None:
        return False
    return hmac.compare_digest(username, USERNAME) and hmac.compare_digest(password, PASSWORD)

def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))
