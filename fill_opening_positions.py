"""
fill_opening_positions.py — isi broker_position_opening dari 1 Jan 2025 - 31 Des 2025.

Jalankan:
    python fill_opening_positions.py
    python fill_opening_positions.py --tickers BBCA BBRI TLKM
"""

import argparse
import logging
import math
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


def run(tickers: list[str] | None = None) -> dict:
    from app.db import supabase
    from app.services.arjum_client import get_broker_summary

    if tickers is None:
        res = supabase.table("stocks").select("ticker,id").eq("is_active", True).execute()
        stocks = {r["ticker"]: r["id"] for r in res.data}
    else:
        res = supabase.table("stocks").select("ticker,id").in_("ticker", tickers).execute()
        stocks = {r["ticker"]: r["id"] for r in res.data}

    log.info(f"fill_opening: {len(stocks)} tickers | {START_DATE} → {END_DATE}")
    success, failed = 0, 0

    for i, (ticker, stock_id) in enumerate(stocks.items(), 1):
        try:
            data = get_broker_summary(ticker, start_date=START_DATE, end_date=END_DATE)
            brokers = data.get("brokers", [])
            if not brokers:
                log.warning(f"[{i}/{len(stocks)}] {ticker}: empty response, skip")
                continue

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
                for j in range(0, len(rows), 500):
                    supabase.table("broker_position_opening").upsert(
                        rows[j:j+500], on_conflict="stock_id,broker_code,start_date"
                    ).execute()

            log.info(f"[{i}/{len(stocks)}] {ticker}: {len(rows)} brokers")
            success += 1

        except Exception as e:
            log.error(f"[{i}/{len(stocks)}] {ticker} FAILED: {e}")
            failed += 1

        time.sleep(0.4)

    result = {
        "start_date": START_DATE,
        "end_date": END_DATE,
        "total": len(stocks),
        "success": success,
        "failed": failed,
    }
    log.info(f"fill_opening done: {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    args = parser.parse_args()
    tickers = [t.upper() for t in args.tickers] if args.tickers else None
    print(run(tickers=tickers))
