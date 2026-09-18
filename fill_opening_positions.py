"""
fill_opening_positions.py

Script 1x jalan untuk mengisi broker_position_opening.

Strategi:
- Gunakan /api/broker-summary dengan range 2025-01-01 s/d 2026-09-01
  untuk mendapat total buy/sell per broker selama periode tersebut.
- Posisi "opening" yang disimpan adalah NET ACTIVITY broker selama range itu,
  dengan start_date = 2025-01-01.
- is_estimated = True karena ini akumulasi transaksi, bukan snapshot posisi riil.

Jalankan:
    python fill_opening_positions.py
    python fill_opening_positions.py --tickers BBCA BBRI TLKM
"""

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

START_DATE = "2025-01-01"
END_DATE = "2026-09-01"


def get_active_tickers() -> list[str]:
    from app.db import supabase
    res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
    return [r["ticker"] for r in res.data]


def fill_opening_for_ticker(ticker: str, stock_id: int) -> int:
    from app.db import supabase
    from app.services.arjum_client import get_broker_summary

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
        buy_vol = int(b.get("bvol") or 0)   # shares
        sell_val = float(b.get("sval") or 0)
        sell_vol = int(b.get("svol") or 0)  # shares

        net_vol = buy_vol - sell_vol         # shares
        net_val = buy_val - sell_val

        # skip broker yang tidak aktif sama sekali
        if buy_vol == 0 and sell_vol == 0:
            continue

        opening_lot = net_vol // 100         # lot
        opening_value = round(net_val, 2)

        # avg price: pakai buy_avg jika net beli, sell_avg jika net jual
        if buy_vol > 0:
            buy_avg = buy_val / buy_vol
        else:
            buy_avg = None

        if sell_vol > 0:
            sell_avg = sell_val / sell_vol
        else:
            sell_avg = None

        if net_vol >= 0:
            avg_price = round(buy_avg, 2) if buy_avg else None
        else:
            avg_price = round(sell_avg, 2) if sell_avg else None

        rows.append({
            "stock_id": stock_id,
            "broker_code": broker_code,
            "start_date": START_DATE,
            "opening_lot": opening_lot,
            "opening_value": opening_value,
            "opening_average_price": avg_price,
            "source": f"arjum_broker_summary_{START_DATE}_{END_DATE}",
            "is_estimated": True,
        })

    if rows:
        # upsert batch
        for i in range(0, len(rows), 500):
            supabase.table("broker_position_opening").upsert(
                rows[i:i+500],
                on_conflict="stock_id,broker_code,start_date"
            ).execute()

    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    args = parser.parse_args()

    from app.db import supabase

    tickers = [t.upper() for t in args.tickers] if args.tickers else get_active_tickers()
    log.info(f"Fill opening positions: {len(tickers)} tickers | {START_DATE} → {END_DATE}")

    success, failed = 0, 0

    for i, ticker in enumerate(tickers, 1):
        try:
            res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
            if not res.data:
                log.warning(f"[{i}/{len(tickers)}] {ticker}: not in stocks table, skip")
                continue
            stock_id = res.data["id"]

            count = fill_opening_for_ticker(ticker, stock_id)
            log.info(f"[{i}/{len(tickers)}] {ticker}: {count} brokers upserted")
            success += 1

        except Exception as e:
            log.error(f"[{i}/{len(tickers)}] {ticker} FAILED: {e}")
            failed += 1

        time.sleep(0.4)  # jaga rate limit

    log.info(f"Selesai. success={success} failed={failed}")


if __name__ == "__main__":
    main()
