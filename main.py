from fastapi import FastAPI
from app.api.v1.register import router as agent_router

app = FastAPI(title="Muninn Inventory API")

app.include_router(agent_router)

@app.get("/")
def read_root():
    return {"status": "Muninn Core is running"}