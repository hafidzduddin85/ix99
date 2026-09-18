from fastapi import APIRouter, HTTPException, Query
from app.db import supabase

router = APIRouter(prefix="/detail", tags=["detail"])


@router.get("/{ticker}")
def get_stock_detail(ticker: str):
    t = ticker.upper()

    stock_res = (
        supabase.table("stocks")
        .select("id,ticker,company_name,sector,subsector,is_active")
        .eq("ticker", t)
        .single()
        .execute()
    )
    if not stock_res.data:
        raise HTTPException(status_code=404, detail=f"Ticker {t} not found")

    stock = stock_res.data
    stock_id = stock["id"]

    analysis_res = (
        supabase.table("v_stock_analysis")
        .select("*")
        .eq("ticker", t)
        .order("trade_date", desc=True)
        .limit(1)
        .execute()
    )
    analysis = analysis_res.data[0] if analysis_res.data else {}

    return {
        "stock": stock,
        "analysis": analysis,
    }


@router.get("/{ticker}/ohlcv")
def get_ohlcv(ticker: str, limit: int = Query(default=200, le=500)):
    t = ticker.upper()
    stock_res = (
        supabase.table("stocks").select("id").eq("ticker", t).single().execute()
    )
    if not stock_res.data:
        raise HTTPException(status_code=404, detail=f"Ticker {t} not found")

    res = (
        supabase.table("stock_daily")
        .select("trade_date,open,high,low,close,volume,value")
        .eq("stock_id", stock_res.data["id"])
        .order("trade_date", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data
