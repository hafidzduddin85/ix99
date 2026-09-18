from app.db import supabase


def get_broker_summary(stock_id: int, days: int = 30) -> list[dict]:
    """Net buy/sell per broker untuk N hari terakhir."""
    res = (
        supabase.table("broker_daily_transaction")
        .select("broker_code,buy_lot,buy_value,sell_lot,sell_value")
        .eq("stock_id", stock_id)
        .order("trade_date", desc=True)
        .limit(days * 50)  # estimasi max 50 broker per hari
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
        brokers[code]["total_buy_lot"] += row.get("buy_lot") or 0
        brokers[code]["total_buy_value"] += float(row.get("buy_value") or 0)
        brokers[code]["total_sell_lot"] += row.get("sell_lot") or 0
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
        concentration_buy = (
            b["total_buy_lot"] / total_buy * 100 if total_buy > 0 else 0
        )
        concentration_sell = (
            b["total_sell_lot"] / total_sell * 100 if total_sell > 0 else 0
        )

        if net_lot > 0:
            activity = "NET BUYING"
        elif net_lot < 0:
            activity = "NET SELLING"
        else:
            activity = "NEUTRAL"

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


def get_broker_position(stock_id: int) -> list[dict]:
    """Estimated position terbaru per broker dari broker_position_daily."""
    res = (
        supabase.table("broker_position_daily")
        .select("broker_code,trade_date,closing_estimated_lot,closing_estimated_value,estimated_average_price")
        .eq("stock_id", stock_id)
        .order("trade_date", desc=True)
        .limit(200)
        .execute()
    )
    if not res.data:
        return []

    # ambil data terbaru per broker
    seen = set()
    result = []
    for row in res.data:
        code = row["broker_code"]
        if code not in seen:
            seen.add(code)
            result.append(row)

    result.sort(key=lambda x: abs(x.get("closing_estimated_lot") or 0), reverse=True)
    return result
