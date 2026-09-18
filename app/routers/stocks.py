from fastapi import APIRouter, HTTPException, Query
from app.db import supabase

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("")
def list_stocks(
    active_only: bool = True,
    watchlist_only: bool = False,
):
    query = supabase.table("stocks").select("id,ticker,company_name,sector,subsector,is_active")

    if active_only:
        query = query.eq("is_active", True)

    if watchlist_only:
        watchlist = supabase.table("watchlist").select("stock_id").eq("is_active", True).execute()
        ids = [w["stock_id"] for w in watchlist.data]
        if not ids:
            return []
        query = query.in_("id", ids)

    res = query.order("ticker").execute()
    return res.data


@router.get("/{ticker}")
def get_stock(ticker: str):
    res = (
        supabase.table("v_stock_analysis")
        .select("*")
        .eq("ticker", ticker.upper())
        .order("trade_date", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
    return res.data[0]


@router.get("/{ticker}/history")
def get_stock_history(ticker: str, limit: int = Query(default=60, le=500)):
    res = (
        supabase.table("v_stock_analysis")
        .select("*")
        .eq("ticker", ticker.upper())
        .order("trade_date", desc=True)
        .limit(limit)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
    return res.data
