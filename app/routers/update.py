from datetime import date
from fastapi import APIRouter, HTTPException, Query
from app.services.indicator_service import run_indicator_calculation
from app.services.trend_service import run_trend_calculation
from app.services.ingestion_service import ingest_ticker, ingest_stocks
from app.db import supabase

router = APIRouter(prefix="/update", tags=["update"])


def _run_full_pipeline(ticker: str, trade_date: str | None = None) -> dict:
    ingest = ingest_ticker(ticker, trade_date)
    ind = run_indicator_calculation(ticker)
    if "error" in ind:
        return {**ingest, "error": ind["error"]}
    trend = run_trend_calculation(ticker)
    return {"ticker": ticker, "ingest": ingest, "indicators": ind, "trend": trend}


@router.post("/stocks")
def sync_stocks():
    """Sync stocks master dari Arjum market-cap."""
    return ingest_stocks()


@router.post("/{ticker}")
def update_ticker(
    ticker: str,
    trade_date: str = Query(default=None, description="YYYY-MM-DD, default today"),
):
    td = trade_date or date.today().isoformat()
    result = _run_full_pipeline(ticker.upper(), td)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/all/run")
def update_all(
    trade_date: str = Query(default=None, description="YYYY-MM-DD, default today"),
):
    td = trade_date or date.today().isoformat()
    res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
    tickers = [r["ticker"] for r in res.data]

    results = []
    for ticker in tickers:
        results.append(_run_full_pipeline(ticker, td))

    return {"total": len(tickers), "trade_date": td, "results": results}
