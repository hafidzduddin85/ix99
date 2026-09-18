"""
fill_opening_positions.py — script 1x jalan via terminal

Jalankan:
    python fill_opening_positions.py
    python fill_opening_positions.py --tickers BBCA BBRI TLKM
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=None)
    args = parser.parse_args()

    from app.services.opening_service import run_fill_opening

    tickers = [t.upper() for t in args.tickers] if args.tickers else None
    result = run_fill_opening(tickers=tickers)
    print(result)
