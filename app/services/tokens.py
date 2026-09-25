from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_project_token, token_prefix, verify_token
from app.models import ProjectToken


def create_token(db: Session, project_id: UUID, name: str) -> tuple[ProjectToken, str]:
    generated = generate_project_token()
    record = ProjectToken(
        project_id=project_id,
        name=name,
        prefix=generated.prefix,
        token_hash=generated.digest,
    )
    db.add(record)
    db.flush()
    return record, generated.plain


def authenticate_project_token(db: Session, token: str) -> ProjectToken:
    prefix = token_prefix(token)
    if prefix is None:
        raise _unauthorized()
    record = db.scalar(select(ProjectToken).where(ProjectToken.prefix == prefix))
    if (
        record is None
        or record.revoked_at is not None
        or not verify_token(token, record.token_hash)
    ):
        raise _unauthorized()
    record.last_used_at = datetime.now(UTC)
    return record


def revoke_token(db: Session, token_id: UUID) -> ProjectToken:
    record = db.get(ProjectToken, token_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
    return record


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
