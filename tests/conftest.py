import os
from collections.abc import Generator

os.environ.setdefault("MUNNIN_SESSION_SECRET", "test-session-secret-at-least-32-chars")
os.environ.setdefault("MUNNIN_TOKEN_PEPPER", "test-token-pepper-at-least-32-chars")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import create_app
from app.models import AdminUser


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def admin(db: Session) -> AdminUser:
    admin = AdminUser(username="admin", password_hash=hash_password("correct-horse-battery"))
    db.add(admin)
    db.commit()
    return admin


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def logged_in_client(client: TestClient, admin: AdminUser) -> TestClient:
    page = client.get("/login")
    marker = 'name="csrf_token" value="'
    login_csrf = page.text.split(marker, 1)[1].split('"', 1)[0]
    response = client.post(
        "/login",
        data={
            "username": admin.username,
            "password": "correct-horse-battery",
            "csrf_token": login_csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client


@pytest.fixture
def csrf(logged_in_client: TestClient) -> str:
    response = logged_in_client.get("/admin/projects")
    marker = 'name="csrf_token" value="'
    return response.text.split(marker, 1)[1].split('"', 1)[0]
