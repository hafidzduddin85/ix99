import pandas as pd
from app.db import supabase
from app.scoring import calculate_trend_score, classify_trend, check_entry_signal


def _get_stock_id(ticker: str) -> int | None:
    res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
    return res.data["id"] if res.data else None


def _fetch_indicators(stock_id: int) -> pd.DataFrame:
    res = (
        supabase.table("technical_indicators")
        .select("*")
        .eq("stock_id", stock_id)
        .order("trade_date", desc=False)
        .execute()
    )
    if not res.data:
        return pd.DataFrame()
    return pd.DataFrame(res.data)


def _val(row, col):
    v = row.get(col)
    if v is None:
        return None
    try:
        import math
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def run_trend_calculation(ticker: str) -> dict:
    stock_id = _get_stock_id(ticker)
    if not stock_id:
        return {"error": f"Ticker {ticker} not found"}

    df = _fetch_indicators(stock_id)
    if df.empty:
        return {"error": f"No indicator data for {ticker}"}

    rows = []
    for _, row in df.iterrows():
        close = _val(row, "close")
        ema20 = _val(row, "ema20")
        ema50 = _val(row, "ema50")
        ema200 = _val(row, "ema200")
        adx14 = _val(row, "adx14")
        plus_di = _val(row, "plus_di")
        minus_di = _val(row, "minus_di")
        rsi14 = _val(row, "rsi14")
        volume_ratio = _val(row, "volume_ratio")
        higher_high = row.get("higher_high")
        higher_low = row.get("higher_low")
        lower_high = row.get("lower_high")
        lower_low = row.get("lower_low")

        components = calculate_trend_score(
            close, ema20, ema50, ema200,
            adx14, plus_di, minus_di,
            rsi14, volume_ratio,
            higher_high, higher_low, lower_high, lower_low
        )
        score = round(components.total, 2)
        trend_direction, trend_strength = classify_trend(score)
        entry_signal = check_entry_signal(
            ema20, ema50, ema200,
            adx14, plus_di, minus_di,
            rsi14, volume_ratio,
            higher_high, higher_low
        )

        rows.append({
            "stock_id": stock_id,
            "signal_date": str(row["trade_date"]),
            "trend_direction": trend_direction,
            "trend_score": score,
            "trend_strength": trend_strength,
            "ema_signal": components.ema_signal,
            "adx_signal": components.adx_signal,
            "momentum_signal": components.momentum_signal,
            "volume_signal": components.volume_signal,
            "structure_signal": components.structure_signal,
            "entry_signal": entry_signal,
        })

    supabase.table("trend_signals").upsert(
        rows, on_conflict="stock_id,signal_date"
    ).execute()

    return {"ticker": ticker, "rows_processed": len(rows)}
