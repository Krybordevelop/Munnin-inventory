from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1 import admin, agents
from app.core.config import Settings, get_settings
from app.core.database import engine
from app.core.middleware import BodyLimitMiddleware, RequestContextMiddleware, configure_logging
from app.web import router as web_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()
    application = FastAPI(title="Muninn Inventory API", version="0.1.0")
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
        session_cookie="munnin_session",
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=settings.secure_cookies,
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(BodyLimitMiddleware, max_bytes=settings.request_body_limit)
    application.include_router(agents.router)
    application.include_router(admin.router)
    application.include_router(web_router)

    @application.get("/")
    def root() -> dict[str, str]:
        return {"status": "Muninn Core is running"}

    @application.get("/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready")
    def readiness() -> dict[str, str]:
        with Session(engine) as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}

    return application


app = create_app()
