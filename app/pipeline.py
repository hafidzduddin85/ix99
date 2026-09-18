import logging
from datetime import date, datetime
from app.db import supabase
from app.services.ingestion_service import ingest_ticker
from app.services.indicator_service import run_indicator_calculation
from app.services.trend_service import run_trend_calculation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run_daily_update(trade_date: str | None = None) -> dict:
    if trade_date is None:
        trade_date = date.today().isoformat()

    started_at = datetime.utcnow()
    log.info(f"Daily update started — trade_date={trade_date}")

    # Step 1: fetch active tickers dari stocks table (tidak sync dari API)
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
        "total": len(tickers),
        "success": len(success),
        "failed": len(failed),
        "failed_tickers": failed,
    }
