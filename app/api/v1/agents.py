from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from app.api.dependencies import DbSession
from app.schemas.agents import AgentReport, ReportResponse
from app.services.agents import report_inventory
from app.services.tokens import authenticate_project_token

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post("/report", response_model=ReportResponse)
def report(
    payload: AgentReport,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> ReportResponse:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ")
    with db.begin():
        token_record = authenticate_project_token(db, token)
        agent = report_inventory(db, token_record.project_id, payload)
    return ReportResponse.model_validate(agent, from_attributes=True)
