from fastapi import APIRouter, Query
from app.db import supabase

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(
    active_only: bool = True,
    watchlist_only: bool = False,
    trend_direction: str | None = None,
    sector: str | None = None,
    subsector: str | None = None,
    min_trend_score: float | None = None,
    min_adx: float | None = None,
    rsi_min: float | None = None,
    rsi_max: float | None = None,
    min_volume_ratio: float | None = None,
    entry_signal: bool | None = None,
):
    query = supabase.table("v_stock_analysis").select("*")

    if active_only:
        query = query.eq("is_active", True)
    if trend_direction:
        query = query.eq("trend_direction", trend_direction.upper())
    if sector:
        query = query.eq("sector", sector)
    if subsector:
        query = query.eq("subsector", subsector)
    if min_trend_score is not None:
        query = query.gte("trend_score", min_trend_score)
    if min_adx is not None:
        query = query.gte("adx14", min_adx)
    if rsi_min is not None:
        query = query.gte("rsi14", rsi_min)
    if rsi_max is not None:
        query = query.lte("rsi14", rsi_max)
    if min_volume_ratio is not None:
        query = query.gte("volume_ratio", min_volume_ratio)
    if entry_signal is not None:
        query = query.eq("entry_signal", entry_signal)

    if watchlist_only:
        watchlist = supabase.table("watchlist").select("stock_id").eq("is_active", True).execute()
        ids = [w["stock_id"] for w in watchlist.data]
        if not ids:
            return {"summary": {}, "stocks": []}
        query = query.in_("stock_id", ids)

    res = query.order("trend_score", desc=True).execute()
    stocks = res.data

    # summary cards
    directions = ["STRONG UPTREND", "UPTREND", "SIDEWAYS", "DOWNTREND", "STRONG DOWNTREND"]
    summary = {d: 0 for d in directions}
    for s in stocks:
        d = s.get("trend_direction")
        if d in summary:
            summary[d] += 1

    return {"summary": summary, "stocks": stocks}


@router.get("/summary")
def get_summary(active_only: bool = True):
    query = supabase.table("v_stock_analysis").select("trend_direction")
    if active_only:
        query = query.eq("is_active", True)
    res = query.execute()

    directions = ["STRONG UPTREND", "UPTREND", "SIDEWAYS", "DOWNTREND", "STRONG DOWNTREND"]
    summary = {d: 0 for d in directions}
    for row in res.data:
        d = row.get("trend_direction")
        if d in summary:
            summary[d] += 1
    return summary
