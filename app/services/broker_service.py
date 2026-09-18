from app.db import supabase


def _get_stock_id(ticker: str) -> int | None:
    res = supabase.table("stocks").select("id").eq("ticker", ticker).single().execute()
    return res.data["id"] if res.data else None


def get_broker_summary(stock_id: int, days: int = 30) -> list[dict]:
    """
    Net buy/sell per broker dari broker_positioning_daily (historical).
    Agregasi N hari terakhir berdasarkan stock_id.
    """
    # resolve ticker dari stock_id
    res = supabase.table("stocks").select("ticker").eq("id", stock_id).single().execute()
    if not res.data:
        return []
    ticker = res.data["ticker"]

    res = (
        supabase.table("broker_positioning_daily")
        .select("broker_code,buy_volume,buy_value,sell_volume,sell_value,trade_date")
        .eq("ticker", ticker)
        .order("trade_date", desc=True)
        .limit(days * 50)
        .execute()
    )
    if not res.data:
        return []

    brokers: dict[str, dict] = {}
    for row in res.data:
        code = row["broker_code"]
        if code not in brokers:
            brokers[code] = {
                "broker_code": code,
                "total_buy_lot": 0,
                "total_buy_value": 0.0,
                "total_sell_lot": 0,
                "total_sell_value": 0.0,
            }
        brokers[code]["total_buy_lot"] += (row.get("buy_volume") or 0) // 100
        brokers[code]["total_buy_value"] += float(row.get("buy_value") or 0)
        brokers[code]["total_sell_lot"] += (row.get("sell_volume") or 0) // 100
        brokers[code]["total_sell_value"] += float(row.get("sell_value") or 0)

    total_buy = sum(b["total_buy_lot"] for b in brokers.values())
    total_sell = sum(b["total_sell_lot"] for b in brokers.values())

    result = []
    for b in brokers.values():
        net_lot = b["total_buy_lot"] - b["total_sell_lot"]
        net_value = b["total_buy_value"] - b["total_sell_value"]
        buy_sell_ratio = (
            b["total_buy_lot"] / b["total_sell_lot"]
            if b["total_sell_lot"] > 0 else None
        )
        concentration_buy = b["total_buy_lot"] / total_buy * 100 if total_buy > 0 else 0
        concentration_sell = b["total_sell_lot"] / total_sell * 100 if total_sell > 0 else 0

        activity = "NET BUYING" if net_lot > 0 else "NET SELLING" if net_lot < 0 else "NEUTRAL"

        result.append({
            **b,
            "net_lot": net_lot,
            "net_value": net_value,
            "buy_sell_ratio": round(buy_sell_ratio, 2) if buy_sell_ratio else None,
            "concentration_buy_pct": round(concentration_buy, 2),
            "concentration_sell_pct": round(concentration_sell, 2),
            "activity": activity,
        })

    result.sort(key=lambda x: abs(x["net_lot"]), reverse=True)
    return result


def get_broker_snapshot(stock_id: int) -> list[dict]:
    """
    Snapshot terbaru broker dari broker_daily_transaction.
    Digunakan untuk menampilkan kondisi broker hari ini.
    """
    res = (
        supabase.table("broker_daily_transaction")
        .select("broker_code,buy_lot,buy_value,buy_avg,sell_lot,sell_value,sell_avg,trade_date")
        .eq("stock_id", stock_id)
        .order("trade_date", desc=True)
        .execute()
    )
    if not res.data:
        return []

    total_buy = sum((r.get("buy_lot") or 0) for r in res.data)
    total_sell = sum((r.get("sell_lot") or 0) for r in res.data)

    result = []
    for row in res.data:
        buy_lot = row.get("buy_lot") or 0
        sell_lot = row.get("sell_lot") or 0
        net_lot = buy_lot - sell_lot
        net_value = float(row.get("buy_value") or 0) - float(row.get("sell_value") or 0)
        activity = "NET BUYING" if net_lot > 0 else "NET SELLING" if net_lot < 0 else "NEUTRAL"
        result.append({
            "broker_code": row["broker_code"],
            "trade_date": row.get("trade_date"),
            "total_buy_lot": buy_lot,
            "total_buy_value": float(row.get("buy_value") or 0),
            "total_sell_lot": sell_lot,
            "total_sell_value": float(row.get("sell_value") or 0),
            "net_lot": net_lot,
            "net_value": net_value,
            "buy_avg": row.get("buy_avg"),
            "sell_avg": row.get("sell_avg"),
            "concentration_buy_pct": round(buy_lot / total_buy * 100, 2) if total_buy > 0 else 0,
            "concentration_sell_pct": round(sell_lot / total_sell * 100, 2) if total_sell > 0 else 0,
            "activity": activity,
        })

    result.sort(key=lambda x: abs(x["net_lot"]), reverse=True)
    return result


def get_broker_opening(stock_id: int) -> list[dict]:
    """
    Akumulasi net position broker sejak awal periode dari broker_position_opening.
    Data 1 tahun — tidak berubah kecuali di-refresh manual.
    """
    res = (
        supabase.table("broker_position_opening")
        .select("broker_code,start_date,opening_lot,opening_value,opening_average_price,is_estimated")
        .eq("stock_id", stock_id)
        .order("opening_lot", desc=True)
        .execute()
    )
    if not res.data:
        return []

    total_long = sum(r["opening_lot"] for r in res.data if (r.get("opening_lot") or 0) > 0)
    total_short = sum(abs(r["opening_lot"]) for r in res.data if (r.get("opening_lot") or 0) < 0)

    result = []
    for row in res.data:
        lot = row.get("opening_lot") or 0
        result.append({
            "broker_code": row["broker_code"],
            "start_date": row.get("start_date"),
            "opening_lot": lot,
            "opening_value": row.get("opening_value"),
            "opening_average_price": row.get("opening_average_price"),
            "is_estimated": row.get("is_estimated"),
            "side": "NET BUYING" if lot > 0 else "NET SELLING" if lot < 0 else "NEUTRAL",
            "concentration_pct": round(
                lot / total_long * 100 if lot > 0 and total_long > 0
                else abs(lot) / total_short * 100 if lot < 0 and total_short > 0
                else 0, 2
            ),
        })

    return result


    """
    Posisi terbaru per broker dari broker_positioning_daily.
    Ambil baris terbaru per broker_code berdasarkan trade_date.
    """
    res = supabase.table("stocks").select("ticker").eq("id", stock_id).single().execute()
    if not res.data:
        return []
    ticker = res.data["ticker"]

    res = (
        supabase.table("broker_positioning_daily")
        .select("broker_code,trade_date,buy_volume,buy_value,buy_avg,sell_volume,sell_value,sell_avg,net_volume,net_value")
        .eq("ticker", ticker)
        .order("trade_date", desc=True)
        .limit(500)
        .execute()
    )
    if not res.data:
        return []

    seen = set()
    result = []
    for row in res.data:
        code = row["broker_code"]
        if code not in seen:
            seen.add(code)
            result.append(row)

    result.sort(key=lambda x: abs(x.get("net_volume") or 0), reverse=True)
    return result
