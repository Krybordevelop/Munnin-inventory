from fastapi import FastAPI
from app.api.v1.register import router as agent_router
from app.admin.routes import router as admin_router

# 1. Импортируй движок и Base
from app.core.database import engine, Base
# 2. Импортируй модели, чтобы Base о них узнал (ВАЖНО!)
from app.models import host, group, user 

# 3. Эта строка создаст таблицы при запуске, если их еще нет
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Muninn Inventory API")

app.include_router(agent_router)
app.include_router(admin_router)

@app.get("/")
def read_root():
    return {"status": "Muninn Core is running"}