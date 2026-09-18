"""
fill_broker_daily.py — isi broker_positioning_daily dari 1 Jan 2026 - 17 Sep 2026.

Jalankan:
    python fill_broker_daily.py
    python fill_broker_daily.py --tickers BBCA BBRI TLKM
    python fill_broker_daily.py --start 2026-01-01 --end 2026-09-17
"""

import argparse
import logging
import sys
import time
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

DEFAULT_START = "2026-01-01"
DEFAULT_END = "2026-09-17"
CHUNK_DAYS = 30  # ambil per 30 hari agar tidak timeout


def _date_chunks(start: str, end: str, chunk: int) -> list[tuple[str, str]]:
    """Bagi rentang tanggal menjadi chunks."""
    chunks = []
    cur = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    while cur <= end_d:
        chunk_end = min(cur + timedelta(days=chunk - 1), end_d)
        chunks.append((cur.isoformat(), chunk_end.isoformat()))
        cur = chunk_end + timedelta(days=1)
    return chunks


def _parse_rows(ticker: str, trade_date: str, brokers: list) -> list[dict]:
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
        buy_avg = round(buy_val / buy_vol, 2) if buy_vol > 0 else None
        sell_avg = round(sell_val / sell_vol, 2) if sell_vol > 0 else None
        rows.append({
            "trade_date": trade_date,
            "ticker": ticker,
            "broker_code": broker_code,
            "buy_volume": buy_vol,
            "buy_value": buy_val,
            "buy_avg": buy_avg,
            "sell_volume": sell_vol,
            "sell_value": sell_val,
            "sell_avg": sell_avg,
            "net_volume": buy_vol - sell_vol,
            "net_value": round(buy_val - sell_val, 2),
        })
    return rows


def run(tickers: list[str] | None = None, start: str = DEFAULT_START, end: str = DEFAULT_END) -> dict:
    from app.db import supabase
    from app.services.arjum_client import get_broker_summary

    if tickers is None:
        res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
        tickers = [r["ticker"] for r in res.data]

    chunks = _date_chunks(start, end, CHUNK_DAYS)
    log.info(f"fill_broker_daily: {len(tickers)} tickers | {start} → {end} | {len(chunks)} chunks")

    success, failed = 0, 0

    for i, ticker in enumerate(tickers, 1):
        ticker_rows = 0
        ticker_failed = False

        for chunk_start, chunk_end in chunks:
            try:
                data = get_broker_summary(ticker, start_date=chunk_start, end_date=chunk_end)
                brokers = data.get("brokers", [])
                if not brokers:
                    continue

                # API broker-summary mengembalikan agregat per periode, bukan per hari.
                # Simpan dengan trade_date = chunk_end (hari terakhir chunk).
                rows = _parse_rows(ticker, chunk_end, brokers)
                if rows:
                    for j in range(0, len(rows), 500):
                        supabase.table("broker_positioning_daily").upsert(
                            rows[j:j+500],
                            on_conflict="trade_date,ticker,broker_code"
                        ).execute()
                    ticker_rows += len(rows)

                time.sleep(0.3)

            except Exception as e:
                log.error(f"[{i}/{len(tickers)}] {ticker} chunk {chunk_start}~{chunk_end} FAILED: {e}")
                ticker_failed = True

        if ticker_failed:
            failed += 1
        else:
            success += 1

        log.info(f"[{i}/{len(tickers)}] {ticker}: {ticker_rows} rows upserted")

    result = {
        "start_date": start,
        "end_date": end,
        "total": len(tickers),
        "success": success,
        "failed": failed,
    }
    log.info(f"fill_broker_daily done: {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    args = parser.parse_args()
    tickers = [t.upper() for t in args.tickers] if args.tickers else None
    print(run(tickers=tickers, start=args.start, end=args.end))
