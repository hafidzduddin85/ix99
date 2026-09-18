from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db import supabase

router = APIRouter(prefix="/stocks", tags=["stocks"])


class StockIn(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    subsector: str | None = None


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


@router.post("")
def add_stock(body: StockIn):
    """Tambah saham baru atau reaktifkan yang sudah ada."""
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker tidak boleh kosong")

    row = {
        "ticker": ticker,
        "is_active": True,
    }
    if body.company_name:
        row["company_name"] = body.company_name
    if body.sector:
        row["sector"] = body.sector
    if body.subsector:
        row["subsector"] = body.subsector

    supabase.table("stocks").upsert(row, on_conflict="ticker").execute()
    res = supabase.table("stocks").select("*").eq("ticker", ticker).single().execute()
    return res.data


@router.delete("/{ticker}")
def deactivate_stock(ticker: str):
    """Set is_active = false. Data historis tidak dihapus."""
    ticker = ticker.upper()
    res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} tidak ditemukan")

    supabase.table("stocks").update({"is_active": False}).eq("ticker", ticker).execute()
    return {"ticker": ticker, "is_active": False}
