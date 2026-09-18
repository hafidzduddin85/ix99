import os
from fastapi import APIRouter, HTTPException, Header, Query
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


@router.post("/fill-opening")
def trigger_fill_opening(
    x_api_key: str | None = Header(default=None),
    tickers: str | None = Query(default=None, description="Comma-separated tickers, default semua"),
):
    """Isi broker_position_opening dari 1 Jan 2025 - 31 Des 2025."""
    _verify(x_api_key)
    from fill_opening_positions import run
    ticker_list = [t.strip().upper() for t in tickers.split(",")] if tickers else None
    return run(tickers=ticker_list)


@router.post("/fill-broker-daily")
def trigger_fill_broker_daily(
    x_api_key: str | None = Header(default=None),
    tickers: str | None = Query(default=None, description="Comma-separated tickers, default semua"),
    start: str = Query(default="2026-01-01"),
    end: str = Query(default="2026-09-17"),
):
    """Isi broker_positioning_daily untuk rentang tanggal tertentu."""
    _verify(x_api_key)
    from fill_broker_daily import run
    ticker_list = [t.strip().upper() for t in tickers.split(",")] if tickers else None
    return run(tickers=ticker_list, start=start, end=end)


