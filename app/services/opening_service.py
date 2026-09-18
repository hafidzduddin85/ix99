import logging
import time
from app.db import supabase
from app.services.arjum_client import get_broker_summary

log = logging.getLogger(__name__)

START_DATE = "2025-01-01"
END_DATE = "2026-09-17"


def fill_opening_for_ticker(ticker: str, stock_id: int) -> int:
    data = get_broker_summary(ticker, start_date=START_DATE, end_date=END_DATE)
    brokers = data.get("brokers", [])
    if not brokers:
        return 0

    rows = []
    for b in brokers:
        broker_code = b.get("broker_code", "").strip()
        if not broker_code:
            continue
        buy_val = float(b.get("bval") or 0)
        buy_vol = int(b.get("bvol") or 0)
        sell_val = float(b.get("sval") or 0)
        sell_vol = int(b.get("svol") or 0)
        if buy_vol == 0 and sell_vol == 0:
            continue
        net_vol = buy_vol - sell_vol
        net_val = buy_val - sell_val
        buy_avg = round(buy_val / buy_vol, 2) if buy_vol > 0 else None
        sell_avg = round(sell_val / sell_vol, 2) if sell_vol > 0 else None
        avg_price = buy_avg if net_vol >= 0 else sell_avg
        rows.append({
            "stock_id": stock_id,
            "broker_code": broker_code,
            "start_date": START_DATE,
            "opening_lot": net_vol // 100,
            "opening_value": round(net_val, 2),
            "opening_average_price": avg_price,
            "source": f"arjum_broker_summary_{START_DATE}_{END_DATE}",
            "is_estimated": True,
        })

    if rows:
        for i in range(0, len(rows), 500):
            supabase.table("broker_position_opening").upsert(
                rows[i:i+500], on_conflict="stock_id,broker_code,start_date"
            ).execute()

    return len(rows)


def run_fill_opening(tickers: list[str] | None = None) -> dict:
    if tickers is None:
        res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
        tickers = [r["ticker"] for r in res.data]

    log.info(f"fill_opening: {len(tickers)} tickers | {START_DATE} -> {END_DATE}")
    success, failed = 0, 0

    for i, ticker in enumerate(tickers, 1):
        try:
            res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
            if not res.data:
                log.warning(f"[{i}/{len(tickers)}] {ticker}: not found, skip")
                continue
            count = fill_opening_for_ticker(ticker, res.data["id"])
            log.info(f"[{i}/{len(tickers)}] {ticker}: {count} brokers")
            success += 1
        except Exception as e:
            log.error(f"[{i}/{len(tickers)}] {ticker} FAILED: {e}")
            failed += 1
        time.sleep(0.4)

    return {
        "start_date": START_DATE,
        "end_date": END_DATE,
        "total": len(tickers),
        "success": success,
        "failed": failed,
    }
