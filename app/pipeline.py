import logging
from datetime import date, datetime
from app.db import supabase
from app.services.ingestion_service import ingest_stocks, ingest_ticker
from app.services.indicator_service import run_indicator_calculation
from app.services.trend_service import run_trend_calculation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

OPENING_START = "2025-01-01"
OPENING_END = "2026-09-01"


def _get_active_tickers() -> list[str]:
    res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
    return [r["ticker"] for r in res.data]


def run_fill_opening_positions(tickers: list[str] | None = None) -> dict:
    """Isi broker_position_opening dari broker-summary range. Jalankan sekali."""
    import time
    from app.services.arjum_client import get_broker_summary

    if tickers is None:
        tickers = _get_active_tickers()

    log.info(f"fill_opening_positions: {len(tickers)} tickers | {OPENING_START} → {OPENING_END}")
    success, failed = [], []

    for ticker in tickers:
        try:
            res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
            if not res.data:
                continue
            stock_id = res.data["id"]

            data = get_broker_summary(ticker, start_date=OPENING_START, end_date=OPENING_END)
            brokers = data.get("brokers", [])

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
                    "start_date": OPENING_START,
                    "opening_lot": net_vol // 100,
                    "opening_value": round(net_val, 2),
                    "opening_average_price": avg_price,
                    "source": f"arjum_broker_summary_{OPENING_START}_{OPENING_END}",
                    "is_estimated": True,
                })

            if rows:
                for i in range(0, len(rows), 500):
                    supabase.table("broker_position_opening").upsert(
                        rows[i:i+500], on_conflict="stock_id,broker_code,start_date"
                    ).execute()

            log.info(f"[OK] {ticker}: {len(rows)} brokers")
            success.append(ticker)

        except Exception as e:
            log.error(f"[FAIL] {ticker}: {e}")
            failed.append({"ticker": ticker, "error": str(e)})

        time.sleep(0.4)

    return {
        "start_date": OPENING_START,
        "end_date": OPENING_END,
        "total": len(tickers),
        "success": len(success),
        "failed": len(failed),
        "failed_tickers": failed,
    }


def run_daily_update(trade_date: str | None = None) -> dict:
    if trade_date is None:
        trade_date = date.today().isoformat()

    started_at = datetime.utcnow()
    log.info(f"Daily update started — trade_date={trade_date}")

    # Step 1: sync stocks master
    try:
        stocks_result = ingest_stocks()
        log.info(f"Stocks synced: {stocks_result}")
    except Exception as e:
        log.error(f"ingest_stocks failed: {e}")
        stocks_result = {"error": str(e)}

    # Step 2: fetch active tickers
    res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
    tickers = [r["ticker"] for r in res.data]
    log.info(f"Found {len(tickers)} active stocks")

    success, failed = [], []

    for ticker in tickers:
        try:
            # Step 3: ingest OHLCV + broker
            ingest_result = ingest_ticker(ticker, trade_date)
            ohlcv_rows = ingest_result["ohlcv"].get("rows_processed", 0)
            broker_rows = ingest_result["broker"].get("rows_processed", 0)

            # Step 4: calculate indicators
            ind = run_indicator_calculation(ticker)
            if "error" in ind:
                raise ValueError(ind["error"])

            # Step 5: calculate trend score
            trend = run_trend_calculation(ticker)
            if "error" in trend:
                raise ValueError(trend["error"])

            log.info(
                f"[OK] {ticker} — ohlcv={ohlcv_rows} broker={broker_rows} "
                f"indicators={ind['rows_processed']}"
            )
            success.append(ticker)

        except Exception as e:
            log.error(f"[FAIL] {ticker} — {e}")
            failed.append({"ticker": ticker, "error": str(e)})

    finished_at = datetime.utcnow()
    duration = (finished_at - started_at).total_seconds()

    log.info(
        f"Daily update finished in {duration:.1f}s — "
        f"success: {len(success)}, failed: {len(failed)}"
    )

    return {
        "trade_date": trade_date,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round(duration, 1),
        "stocks_sync": stocks_result,
        "total": len(tickers),
        "success": len(success),
        "failed": len(failed),
        "failed_tickers": failed,
    }
