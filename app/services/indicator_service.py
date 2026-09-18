import math
import pandas as pd
from app.db import supabase
from app.indicators import calculate_all


def _get_stock_id(ticker: str) -> int | None:
    res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
    return res.data["id"] if res.data else None


def _fetch_ohlcv(stock_id: int) -> pd.DataFrame:
    res = (
        supabase.table("stock_daily")
        .select("trade_date,open,high,low,close,volume")
        .eq("stock_id", stock_id)
        .order("trade_date", desc=False)
        .execute()
    )
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    return df


def _safe(val):
    """Convert NaN/inf to None for JSON serialization."""
    if val is None:
        return None
    try:
        if math.isnan(val) or math.isinf(val):
            return None
    except TypeError:
        pass
    return val


def run_indicator_calculation(ticker: str) -> dict:
    stock_id = _get_stock_id(ticker)
    if not stock_id:
        return {"error": f"Ticker {ticker} not found"}

    df = _fetch_ohlcv(stock_id)
    if df.empty or len(df) < 20:
        return {"error": f"Insufficient data for {ticker}"}

    df = calculate_all(df)

    rows = []
    for _, row in df.iterrows():
        rows.append({
            "stock_id": stock_id,
            "trade_date": str(row["trade_date"]),
            "close": _safe(row.get("close")),
            "ema20": _safe(row.get("ema20")),
            "ema50": _safe(row.get("ema50")),
            "ema200": _safe(row.get("ema200")),
            "rsi14": _safe(row.get("rsi14")),
            "adx14": _safe(row.get("adx14")),
            "plus_di": _safe(row.get("plus_di")),
            "minus_di": _safe(row.get("minus_di")),
            "atr14": _safe(row.get("atr14")),
            "avg_volume20": _safe(row.get("avg_volume20")),
            "volume_ratio": _safe(row.get("volume_ratio")),
            "higher_high": bool(row["higher_high"]) if pd.notna(row.get("higher_high")) else None,
            "higher_low": bool(row["higher_low"]) if pd.notna(row.get("higher_low")) else None,
            "lower_high": bool(row["lower_high"]) if pd.notna(row.get("lower_high")) else None,
            "lower_low": bool(row["lower_low"]) if pd.notna(row.get("lower_low")) else None,
        })

    supabase.table("technical_indicators").upsert(
        rows, on_conflict="stock_id,trade_date"
    ).execute()

    return {"ticker": ticker, "rows_processed": len(rows)}
