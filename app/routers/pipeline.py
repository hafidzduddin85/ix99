import os
from fastapi import APIRouter, HTTPException, Header
from app.pipeline import run_daily_update

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

PIPELINE_SECRET = os.getenv("PIPELINE_SECRET", "")


def _verify(x_api_key: str | None):
    if not PIPELINE_SECRET:
        return
    if x_api_key != PIPELINE_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/run")
def trigger_pipeline(x_api_key: str | None = Header(default=None)):
    _verify(x_api_key)
    return run_daily_update()

