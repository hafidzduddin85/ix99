import pytest
import pandas as pd
import numpy as np
from app.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_adx,
    calculate_volume_ratio,
    calculate_price_structure,
    calculate_all,
)


def make_df(n=250, seed=42):
    rng = np.random.default_rng(seed)
    close = 1000 + np.cumsum(rng.normal(0, 10, n))
    high = close + rng.uniform(5, 20, n)
    low = close - rng.uniform(5, 20, n)
    open_ = close + rng.normal(0, 5, n)
    volume = rng.integers(1_000_000, 10_000_000, n).astype(float)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "trade_date": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


class TestEMA:
    def test_length(self):
        df = make_df()
        ema = calculate_ema(df["close"], 20)
        assert len(ema) == len(df)

    def test_no_lookahead(self):
        df = make_df(100)
        ema_full = calculate_ema(df["close"], 20)
        ema_partial = calculate_ema(df["close"].iloc[:50], 20)
        # nilai ema pada index 49 harus sama
        assert abs(ema_full.iloc[49] - ema_partial.iloc[49]) < 1e-6

    def test_ema20_lt_ema50_possible(self):
        df = make_df()
        ema20 = calculate_ema(df["close"], 20)
        ema50 = calculate_ema(df["close"], 50)
        # keduanya harus punya nilai valid
        assert ema20.notna().all()
        assert ema50.notna().all()


class TestRSI:
    def test_range(self):
        df = make_df()
        rsi = calculate_rsi(df["close"])
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_length(self):
        df = make_df()
        rsi = calculate_rsi(df["close"])
        assert len(rsi) == len(df)

    def test_no_lookahead(self):
        df = make_df(100)
        rsi_full = calculate_rsi(df["close"])
        rsi_partial = calculate_rsi(df["close"].iloc[:60])
        assert abs(rsi_full.iloc[59] - rsi_partial.iloc[59]) < 1e-6


class TestATR:
    def test_positive(self):
        df = make_df()
        atr = calculate_atr(df["high"], df["low"], df["close"])
        assert (atr.dropna() > 0).all()

    def test_length(self):
        df = make_df()
        atr = calculate_atr(df["high"], df["low"], df["close"])
        assert len(atr) == len(df)


class TestADX:
    def test_adx_positive(self):
        df = make_df()
        adx_df = calculate_adx(df["high"], df["low"], df["close"])
        assert (adx_df["adx14"].dropna() >= 0).all()

    def test_di_columns(self):
        df = make_df()
        adx_df = calculate_adx(df["high"], df["low"], df["close"])
        assert "plus_di" in adx_df.columns
        assert "minus_di" in adx_df.columns

    def test_length(self):
        df = make_df()
        adx_df = calculate_adx(df["high"], df["low"], df["close"])
        assert len(adx_df) == len(df)


class TestVolumeRatio:
    def test_ratio_positive(self):
        df = make_df()
        vol_df = calculate_volume_ratio(df["volume"])
        assert (vol_df["volume_ratio"].dropna() > 0).all()

    def test_null_before_period(self):
        df = make_df(30)
        vol_df = calculate_volume_ratio(df["volume"], period=20)
        # sebelum 20 bar harus null
        assert vol_df["avg_volume20"].iloc[:19].isna().all()


class TestPriceStructure:
    def test_columns(self):
        df = make_df()
        struct = calculate_price_structure(df["high"], df["low"])
        for col in ["higher_high", "higher_low", "lower_high", "lower_low"]:
            assert col in struct.columns

    def test_boolean_values(self):
        df = make_df()
        struct = calculate_price_structure(df["high"], df["low"])
        valid = struct.dropna()
        for col in ["higher_high", "higher_low", "lower_high", "lower_low"]:
            assert valid[col].dtype == bool


class TestCalculateAll:
    def test_all_columns_present(self):
        df = make_df()
        result = calculate_all(df)
        expected = [
            "ema20", "ema50", "ema200", "rsi14",
            "adx14", "plus_di", "minus_di", "atr14",
            "avg_volume20", "volume_ratio",
            "higher_high", "higher_low", "lower_high", "lower_low",
        ]
        for col in expected:
            assert col in result.columns, f"Missing column: {col}"

    def test_ema200_null_before_200_bars(self):
        df = make_df(150)
        result = calculate_all(df)
        assert result["ema200"].isna().all()

    def test_ema200_valid_after_200_bars(self):
        df = make_df(250)
        result = calculate_all(df)
        assert result["ema200"].iloc[199:].notna().all()

    def test_no_future_data(self):
        """Nilai indikator pada baris T tidak boleh berubah saat data T+1 ditambahkan."""
        df = make_df(100)
        result_100 = calculate_all(df.copy())
        result_50 = calculate_all(df.iloc[:50].copy())
        assert abs(result_100["ema20"].iloc[49] - result_50["ema20"].iloc[49]) < 1e-6
        assert abs(result_100["rsi14"].iloc[49] - result_50["rsi14"].iloc[49]) < 1e-6
