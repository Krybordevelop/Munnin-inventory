import hashlib
import hmac
import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


@dataclass(frozen=True)
class GeneratedToken:
    plain: str
    prefix: str
    digest: str


def _token_digest(token: str) -> str:
    pepper = get_settings().token_pepper.get_secret_value().encode()
    return hmac.new(pepper, token.encode(), hashlib.sha256).hexdigest()


def generate_project_token() -> GeneratedToken:
    identifier = secrets.token_hex(6)
    token = f"mun_{identifier}_{secrets.token_urlsafe(32)}"
    return GeneratedToken(token, f"mun_{identifier}", _token_digest(token))


def token_prefix(token: str) -> str | None:
    parts = token.split("_", 2)
    if len(parts) != 3 or parts[0] != "mun" or len(parts[1]) != 12:
        return None
    return f"mun_{parts[1]}"


def verify_token(token: str, expected_digest: str) -> bool:
    return hmac.compare_digest(_token_digest(token), expected_digest)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, digest: str) -> bool:
    try:
        return password_hasher.verify(digest, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)
