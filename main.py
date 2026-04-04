from fastapi import FastAPI
from app.api.v1.register import router as agent_router
from app.admin.routes import router as admin_router
from app.admin.auth import router as auth_router

from app.core.database import engine, Base
from app.models import host, group, user 

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Muninn Inventory API")

app.include_router(agent_router)
app.include_router(admin_router)
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"status": "Muninn Core is running"}