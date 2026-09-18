import logging
from datetime import date
from app.db import supabase
from app.services.arjum_client import get_market_cap, get_history, get_broker_summary

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stocks
# ---------------------------------------------------------------------------

def ingest_stocks() -> dict:
    """
    Sync stocks table dari /api/market-cap (semua halaman).
    Upsert berdasarkan ticker. Tidak menghapus data lama.
    """
    page, total_pages = 1, 1
    upserted = 0

    while page <= total_pages:
        data = get_market_cap(page=page)
        total_pages = data.get("total_pages", 1)

        rows = []
        for item in data.get("data", []):
            ticker = item.get("code", "").upper().strip()
            name = item.get("name", "")
            if not ticker:
                continue
            rows.append({
                "ticker": ticker,
                "company_name": name,
                "is_active": True,
            })

        if rows:
            supabase.table("stocks").upsert(
                rows, on_conflict="ticker"
            ).execute()
            upserted += len(rows)

        page += 1

    log.info(f"ingest_stocks: upserted {upserted} rows")
    return {"upserted": upserted}


# ---------------------------------------------------------------------------
# Stock Daily (OHLCV)
# ---------------------------------------------------------------------------

def _get_stock_id(ticker: str) -> int | None:
    res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
    return res.data["id"] if res.data else None


def ingest_ohlcv(ticker: str) -> dict:
    """
    Ingest OHLCV dari /api/history/{ticker} ke stock_daily.
    Upsert berdasarkan (stock_id, trade_date).
    """
    stock_id = _get_stock_id(ticker)
    if not stock_id:
        return {"error": f"Ticker {ticker} not found in stocks table"}

    data = get_history(ticker)
    rows_raw = data.get("rows", [])
    if not rows_raw:
        return {"ticker": ticker, "rows_processed": 0}

    rows = []
    for item in rows_raw:
        trade_date = item.get("date")
        if not trade_date:
            continue
        rows.append({
            "stock_id": stock_id,
            "trade_date": trade_date,
            "open": item.get("open"),
            "high": item.get("high"),
            "low": item.get("low"),
            "close": item.get("close"),
            "volume": int(item["volume"]) if item.get("volume") is not None else None,
            "value": item.get("value"),
        })

    if rows:
        # upsert in batches of 500
        for i in range(0, len(rows), 500):
            supabase.table("stock_daily").upsert(
                rows[i:i+500], on_conflict="stock_id,trade_date"
            ).execute()

    log.info(f"ingest_ohlcv {ticker}: {len(rows)} rows")
    return {"ticker": ticker, "rows_processed": len(rows)}


# ---------------------------------------------------------------------------
# Broker — helpers
# ---------------------------------------------------------------------------

def _parse_broker_rows(ticker: str, stock_id: int, trade_date: str, brokers: list) -> tuple[list, list]:
    """
    Parse raw broker list dari API menjadi dua set rows:
    - snapshot_rows  → broker_daily_transaction (pakai stock_id, buy_lot/sell_lot)
    - historical_rows → broker_positioning_daily (pakai ticker, buy_volume/sell_volume)
    """
    snapshot_rows = []
    historical_rows = []

    for b in brokers:
        broker_code = b.get("broker_code", "").strip()
        if not broker_code:
            continue

        buy_val = float(b.get("bval") or 0)
        buy_vol = int(b.get("bvol") or 0)
        sell_val = float(b.get("sval") or 0)
        sell_vol = int(b.get("svol") or 0)

        buy_avg = round(buy_val / buy_vol, 2) if buy_vol > 0 else None
        sell_avg = round(sell_val / sell_vol, 2) if sell_vol > 0 else None
        net_vol = buy_vol - sell_vol
        net_val = buy_val - sell_val

        snapshot_rows.append({
            "stock_id": stock_id,
            "trade_date": trade_date,
            "broker_code": broker_code,
            "buy_lot": buy_vol // 100,
            "buy_value": buy_val,
            "buy_avg": buy_avg,
            "sell_lot": sell_vol // 100,
            "sell_value": sell_val,
            "sell_avg": sell_avg,
        })

        historical_rows.append({
            "trade_date": trade_date,
            "ticker": ticker,
            "broker_code": broker_code,
            "buy_volume": buy_vol,
            "buy_value": buy_val,
            "buy_avg": buy_avg,
            "sell_volume": sell_vol,
            "sell_value": sell_val,
            "sell_avg": sell_avg,
            "net_volume": net_vol,
            "net_value": net_val,
        })

    return snapshot_rows, historical_rows


# ---------------------------------------------------------------------------
# Broker Daily Transaction (snapshot) + Broker Positioning Daily (historical)
# ---------------------------------------------------------------------------

def ingest_broker_transactions(ticker: str, trade_date: str) -> dict:
    """
    Ingest broker summary dari Arjum API:
    - broker_daily_transaction: DELETE snapshot lama, INSERT terbaru.
      DELETE hanya dilakukan setelah data API berhasil diambil dan divalidasi.
    - broker_positioning_daily: UPSERT historical, tidak pernah dihapus.
    """
    stock_id = _get_stock_id(ticker)
    if not stock_id:
        return {"error": f"Ticker {ticker} not found in stocks table"}

    # Ambil data dari API dulu — jangan DELETE sebelum data valid
    try:
        data = get_broker_summary(ticker, start_date=trade_date, end_date=trade_date)
    except Exception as e:
        log.error(f"ingest_broker_transactions {ticker}: API error — {e}")
        return {"error": f"API error: {e}", "ticker": ticker, "trade_date": trade_date, "rows_processed": 0}

    brokers = data.get("brokers", [])
    if not brokers:
        log.warning(f"ingest_broker_transactions {ticker} {trade_date}: empty response, snapshot retained")
        return {"ticker": ticker, "trade_date": trade_date, "rows_processed": 0}

    snapshot_rows, historical_rows = _parse_broker_rows(ticker, stock_id, trade_date, brokers)

    if not snapshot_rows:
        return {"ticker": ticker, "trade_date": trade_date, "rows_processed": 0}

    # Data valid — aman untuk replace snapshot
    supabase.table("broker_daily_transaction").delete().eq("stock_id", stock_id).execute()
    supabase.table("broker_daily_transaction").insert(snapshot_rows).execute()

    # UPSERT historical — tidak pernah dihapus
    for i in range(0, len(historical_rows), 500):
        supabase.table("broker_positioning_daily").upsert(
            historical_rows[i:i+500],
            on_conflict="trade_date,ticker,broker_code"
        ).execute()

    log.info(f"ingest_broker_transactions {ticker} {trade_date}: snapshot={len(snapshot_rows)} historical={len(historical_rows)}")
    return {"ticker": ticker, "trade_date": trade_date, "rows_processed": len(snapshot_rows)}


# ---------------------------------------------------------------------------
# Full ingestion untuk satu ticker
# ---------------------------------------------------------------------------

def ingest_ticker(ticker: str, trade_date: str | None = None) -> dict:
    """
    Ingest OHLCV + broker transactions untuk satu ticker.
    trade_date default = hari ini.
    """
    if trade_date is None:
        trade_date = date.today().isoformat()

    ohlcv = ingest_ohlcv(ticker)
    broker = ingest_broker_transactions(ticker, trade_date)

    return {
        "ticker": ticker,
        "ohlcv": ohlcv,
        "broker": broker,
    }
