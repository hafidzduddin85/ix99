from fastapi import APIRouter, HTTPException, Query
from app.db import supabase
from app.services.broker_service import get_broker_summary, get_broker_position, get_broker_snapshot, get_broker_opening

router = APIRouter(prefix="/broker", tags=["broker"])


def _get_stock_id(ticker: str) -> int | None:
    res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
    return res.data["id"] if res.data else None


@router.get("/{ticker}/summary")
def broker_summary(ticker: str, days: int = Query(default=30, le=90)):
    stock_id = _get_stock_id(ticker.upper())
    if not stock_id:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
    return get_broker_summary(stock_id, days)



@router.get("/{ticker}/snapshot")
def broker_snapshot(ticker: str):
    """Snapshot broker terbaru dari broker_daily_transaction."""
    stock_id = _get_stock_id(ticker.upper())
    if not stock_id:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
    return get_broker_snapshot(stock_id)


@router.get("/{ticker}/flow")
def broker_flow(ticker: str, days: int = Query(default=30, le=90)):
    """Combined broker summary + position untuk stock detail page."""
    stock_id = _get_stock_id(ticker.upper())
    if not stock_id:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")

    summary = get_broker_summary(stock_id, days)
    position = get_broker_position(stock_id)
    opening = get_broker_opening(stock_id)

    net_buying = [b for b in summary if b["activity"] == "NET BUYING"][:10]
    net_selling = [b for b in summary if b["activity"] == "NET SELLING"][:10]

    return {
        "top_net_buying": net_buying,
        "top_net_selling": net_selling,
        "positions": position[:20],
        "opening": opening,
    }
