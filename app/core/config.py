from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MUNNIN_", env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./munnin.db"
    session_secret: SecretStr = Field(min_length=32)
    token_pepper: SecretStr = Field(min_length=32)
    secure_cookies: bool = False
    request_body_limit: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    session_max_age: int = Field(default=28_800, ge=300)
    login_attempts: int = Field(default=5, ge=1)
    login_window_seconds: int = Field(default=300, ge=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()
