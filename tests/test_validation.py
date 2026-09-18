import pytest
import pandas as pd
import numpy as np


def validate_ohlcv(df: pd.DataFrame) -> list[str]:
    errors = []
    if df["close"].isna().any():
        errors.append("close contains NULL values")
    if (df["high"] < df["low"]).any():
        errors.append("high < low detected")
    if (df["high"] < df["open"]).any():
        errors.append("high < open detected")
    if (df["high"] < df["close"]).any():
        errors.append("high < close detected")
    if (df["low"] > df["open"]).any():
        errors.append("low > open detected")
    if (df["low"] > df["close"]).any():
        errors.append("low > close detected")
    if (df["volume"] < 0).any():
        errors.append("negative volume detected")
    return errors


def check_duplicates(df: pd.DataFrame, key_cols: list[str]) -> bool:
    return df.duplicated(subset=key_cols).any()


class TestOHLCVValidation:
    def make_valid_df(self):
        return pd.DataFrame({
            "trade_date": pd.date_range("2024-01-01", periods=5),
            "open":  [100, 102, 101, 103, 105],
            "high":  [105, 106, 104, 107, 108],
            "low":   [98,  100, 99,  101, 103],
            "close": [102, 101, 103, 105, 107],
            "volume": [1000, 2000, 1500, 3000, 2500],
        })

    def test_valid_data_passes(self):
        df = self.make_valid_df()
        assert validate_ohlcv(df) == []

    def test_null_close(self):
        df = self.make_valid_df()
        df.loc[0, "close"] = np.nan
        errors = validate_ohlcv(df)
        assert any("NULL" in e for e in errors)

    def test_high_less_than_low(self):
        df = self.make_valid_df()
        df.loc[0, "high"] = 90
        df.loc[0, "low"] = 95
        errors = validate_ohlcv(df)
        assert any("high < low" in e for e in errors)

    def test_negative_volume(self):
        df = self.make_valid_df()
        df.loc[0, "volume"] = -100
        errors = validate_ohlcv(df)
        assert any("negative volume" in e for e in errors)

    def test_high_less_than_close(self):
        df = self.make_valid_df()
        df.loc[0, "high"] = 99
        df.loc[0, "close"] = 102
        errors = validate_ohlcv(df)
        assert any("high < close" in e for e in errors)


class TestDuplicateDetection:
    def test_no_duplicates(self):
        df = pd.DataFrame({
            "stock_id": [1, 1, 1],
            "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        })
        assert check_duplicates(df, ["stock_id", "trade_date"]) is False

    def test_duplicate_detected(self):
        df = pd.DataFrame({
            "stock_id": [1, 1, 1],
            "trade_date": ["2024-01-01", "2024-01-01", "2024-01-03"],
        })
        assert check_duplicates(df, ["stock_id", "trade_date"]) is True

    def test_duplicate_ticker(self):
        df = pd.DataFrame({"ticker": ["BBCA", "BBCA", "TLKM"]})
        assert check_duplicates(df, ["ticker"]) is True


class TestIndicatorDataLeakage:
    def test_ema_no_lookahead(self):
        from app.indicators import calculate_ema
        import pandas as pd
        close = pd.Series(range(1, 101), dtype=float)
        ema_full = calculate_ema(close, 20)
        ema_partial = calculate_ema(close.iloc[:50], 20)
        assert abs(ema_full.iloc[49] - ema_partial.iloc[49]) < 1e-6

    def test_rsi_no_lookahead(self):
        from app.indicators import calculate_rsi
        import pandas as pd
        close = pd.Series(range(1, 101), dtype=float)
        rsi_full = calculate_rsi(close)
        rsi_partial = calculate_rsi(close.iloc[:60])
        assert abs(rsi_full.iloc[59] - rsi_partial.iloc[59]) < 1e-6

    def test_atr_no_lookahead(self):
        from app.indicators import calculate_atr
        import numpy as np
        rng = np.random.default_rng(0)
        close = pd.Series(1000 + np.cumsum(rng.normal(0, 10, 100)))
        high = close + rng.uniform(5, 20, 100)
        low = close - rng.uniform(5, 20, 100)
        atr_full = calculate_atr(high, low, close)
        atr_partial = calculate_atr(high.iloc[:60], low.iloc[:60], close.iloc[:60])
        assert abs(atr_full.iloc[59] - atr_partial.iloc[59]) < 1e-6
