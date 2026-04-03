from fastapi import FastAPI
from app.api.v1.register import router as agent_router
from app.admin.routes import router as admin_router

app = FastAPI(title="Muninn Inventory API")

# Эндпоинты для агентов
app.include_router(agent_router)

# Эндпоинты для админки (интерфейс пользователя)
app.include_router(admin_router)

@app.get("/")
def read_root():
    return {"status": "Muninn Core is running"}