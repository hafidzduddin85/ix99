import os
from fastapi import APIRouter, HTTPException, Header, Query
from app.pipeline import run_daily_update, run_fill_opening_positions

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


@router.post("/fill-opening")
def trigger_fill_opening(
    x_api_key: str | None = Header(default=None),
    tickers: list[str] = Query(default=None),
):
    """Isi broker_position_opening sekali. Opsional filter ticker."""
    _verify(x_api_key)
    return run_fill_opening_positions(tickers=tickers)
