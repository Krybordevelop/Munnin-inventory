import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.models.group import Group
from app.models.host import Host
from main import app
from fastapi.testclient import TestClient

# Используем SQLite в памяти для быстрых тестов
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine) # Создаем все таблицы (groups, hosts)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

# --- НОВАЯ ФИКСТУРА ---
@pytest.fixture
def test_group(db):
    """Создает тестовую группу в БД для проверки регистрации агентов"""
    group = Group(name="Test Servers", token="secret-token-123")
    db.add(group)
    db.commit()
    db.refresh(group)
    return group