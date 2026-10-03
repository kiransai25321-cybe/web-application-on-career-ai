import time
import secrets
import re
from typing import Dict, Tuple
import bcrypt
from starlette.requests import Request
from starlette.responses import Response

# In-memory rate limiting: key -> list of failure timestamps
# key format: f"{client_ip}:{identifier}"
FAILED_ATTEMPTS: Dict[str, list[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60  # 15 minutes


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validates password strength:
    - At least 8 characters
    - At least one letter
    - At least one number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, ""


def check_rate_limit(client_ip: str, identifier: str) -> Tuple[bool, int]:
    """
    Check if identifier/ip is rate limited.
    Returns (is_limited, remaining_lockout_seconds).
    """
    key = f"{client_ip}:{identifier.lower().strip()}"
    now = time.time()
    
    attempts = FAILED_ATTEMPTS.get(key, [])
    # Filter attempts within lockout window
    recent_attempts = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    FAILED_ATTEMPTS[key] = recent_attempts

    if len(recent_attempts) >= MAX_FAILED_ATTEMPTS:
        oldest_relevant = recent_attempts[0]
        remaining = int(LOCKOUT_SECONDS - (now - oldest_relevant))
        return True, max(1, remaining)
    
    return False, 0


def record_failed_attempt(client_ip: str, identifier: str):
    """Record a failed login attempt."""
    key = f"{client_ip}:{identifier.lower().strip()}"
    now = time.time()
    attempts = FAILED_ATTEMPTS.get(key, [])
    attempts.append(now)
    FAILED_ATTEMPTS[key] = attempts


def reset_failed_attempts(client_ip: str, identifier: str):
    """Clear failed login attempts after successful authentication."""
    key = f"{client_ip}:{identifier.lower().strip()}"
    if key in FAILED_ATTEMPTS:
        del FAILED_ATTEMPTS[key]


# --- CSRF Protection ---
def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def get_or_set_csrf_token(request: Request) -> str:
    """Retrieve existing CSRF token from session or generate a new one."""
    token = request.session.get("csrf_token")
    if not token:
        token = generate_csrf_token()
        request.session["csrf_token"] = token
    return token


def verify_csrf_token(request: Request, submitted_token: str) -> bool:
    """Verify that submitted CSRF token matches session token."""
    session_token = request.session.get("csrf_token")
    if not session_token or not submitted_token:
        return False
    return secrets.compare_digest(session_token, submitted_token)
