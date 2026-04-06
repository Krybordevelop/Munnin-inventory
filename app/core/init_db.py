from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.group import Group
from app.core.security import get_password_hash

def init_db():
    # 1. Создаем таблицы, если их нет
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        default_group = db.query(Group).filter(Group.name == "Unassigned").first()
        if not default_group:
            default_group = Group(
                name="Unassigned", 
                token="default-public-token",
                is_mutable=False # Запрещаем удаление через API
            )
            db.add(default_group)
            db.commit()

        # 3. Создаем супер-админа (только если таблица пуста)
        admin_exists = db.query(User).filter(User.username == "admin").first()
        if not admin_exists:
            new_admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                is_admin=True,
                is_active=True
            )
            db.add(new_admin)
            print("--- Initial admin user created (admin/admin123) ---")
        
        db.commit()
    except Exception as e:
        print(f"Error during DB initialization: {e}")
        db.rollback()
    finally:
        db.close()