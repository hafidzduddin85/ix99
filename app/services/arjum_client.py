import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://stock.arjum.com"
API_KEY = os.getenv("ARJUNA_API_KEY")

if not API_KEY:
    raise RuntimeError("ARJUNA_API_KEY must be set")

HEADERS = {"X-API-Key": API_KEY}
TIMEOUT = 30.0


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()


def get_market_cap(page: int = 1) -> dict:
    return _get("/api/market-cap", params={"page": page})


def get_history(ticker: str) -> dict:
    return _get(f"/api/history/{ticker}")


def get_broker_summary(ticker: str, start_date: str, end_date: str) -> dict:
    return _get(f"/api/broker-summary/{ticker}", params={
        "start_date": start_date,
        "end_date": end_date,
    })


def get_broker_accumulation(ticker: str) -> dict:
    return _get(f"/api/broker-accumulation/{ticker}")
