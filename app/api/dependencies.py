import hmac
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models import AdminUser

DbSession = Annotated[Session, Depends(get_db)]


def current_admin(request: Request, db: DbSession) -> AdminUser:
    raw_id = request.session.get("admin_id")
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        admin_id = UUID(raw_id)
    except ValueError:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Authentication required") from None
    admin = db.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Authentication required")
    return admin


CurrentAdmin = Annotated[AdminUser, Depends(current_admin)]


def require_csrf(request: Request) -> None:
    expected = request.session.get("csrf")
    supplied = request.headers.get("x-csrf-token")
    if not expected or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


CsrfProtected = Annotated[None, Depends(require_csrf)]


@dataclass
class LoginLimiter:
    attempts: dict[str, deque[float]]

    def __init__(self) -> None:
        self.attempts = defaultdict(deque)

    def allowed(self, key: str) -> bool:
        settings = get_settings()
        now = time.monotonic()
        queue = self.attempts[key]
        while queue and queue[0] <= now - settings.login_window_seconds:
            queue.popleft()
        return len(queue) < settings.login_attempts

    def failed(self, key: str) -> None:
        self.attempts[key].append(time.monotonic())

    def succeeded(self, key: str) -> None:
        self.attempts.pop(key, None)


login_limiter = LoginLimiter()
