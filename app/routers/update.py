from fastapi import APIRouter, HTTPException
from app.services.indicator_service import run_indicator_calculation
from app.services.trend_service import run_trend_calculation
from app.db import supabase

router = APIRouter(prefix="/update", tags=["update"])


def _run_full_pipeline(ticker: str) -> dict:
    ind = run_indicator_calculation(ticker)
    if "error" in ind:
        return ind
    trend = run_trend_calculation(ticker)
    return {"ticker": ticker, "indicators": ind, "trend": trend}


@router.post("/{ticker}")
def update_ticker(ticker: str):
    result = _run_full_pipeline(ticker.upper())
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/all/run")
def update_all():
    res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
    tickers = [r["ticker"] for r in res.data]

    results = []
    for ticker in tickers:
        results.append(_run_full_pipeline(ticker))

    return {"total": len(tickers), "results": results}
