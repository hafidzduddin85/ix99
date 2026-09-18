import logging
from datetime import datetime
from app.db import supabase
from app.services.indicator_service import run_indicator_calculation
from app.services.trend_service import run_trend_calculation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run_daily_update() -> dict:
    started_at = datetime.utcnow()
    log.info("Daily update started")

    res = supabase.table("stocks").select("ticker").eq("is_active", True).execute()
    tickers = [r["ticker"] for r in res.data]
    log.info(f"Found {len(tickers)} active stocks")

    success, failed = [], []

    for ticker in tickers:
        try:
            ind = run_indicator_calculation(ticker)
            if "error" in ind:
                raise ValueError(ind["error"])

            trend = run_trend_calculation(ticker)
            if "error" in trend:
                raise ValueError(trend["error"])

            log.info(f"[OK] {ticker} — {ind['rows_processed']} rows")
            success.append(ticker)

        except Exception as e:
            log.error(f"[FAIL] {ticker} — {e}")
            failed.append({"ticker": ticker, "error": str(e)})

    finished_at = datetime.utcnow()
    duration = (finished_at - started_at).total_seconds()

    log.info(f"Daily update finished in {duration:.1f}s — success: {len(success)}, failed: {len(failed)}")

    return {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round(duration, 1),
        "total": len(tickers),
        "success": len(success),
        "failed": len(failed),
        "failed_tickers": failed,
    }
