import pandas as pd
import numpy as np


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.DataFrame:
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    plus_dm = high - prev_high
    minus_dm = prev_low - low
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr = calculate_atr(high, low, close, period)
    plus_di = 100 * (plus_dm.ewm(com=period - 1, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(com=period - 1, adjust=False).mean() / atr)

    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(com=period - 1, adjust=False).mean()

    return pd.DataFrame({"adx14": adx, "plus_di": plus_di, "minus_di": minus_di})


def calculate_volume_ratio(volume: pd.Series, period: int = 20) -> pd.DataFrame:
    avg_volume = volume.rolling(window=period, min_periods=period).mean()
    ratio = volume / avg_volume.replace(0, np.nan)
    return pd.DataFrame({"avg_volume20": avg_volume, "volume_ratio": ratio})


def calculate_price_structure(high: pd.Series, low: pd.Series, window: int = 10) -> pd.DataFrame:
    roll_high = high.rolling(window=window, min_periods=window)
    roll_low = low.rolling(window=window, min_periods=window)

    prev_max_high = roll_high.max().shift(window)
    prev_min_low = roll_low.min().shift(window)
    curr_max_high = roll_high.max()
    curr_min_low = roll_low.min()

    higher_high = curr_max_high > prev_max_high
    higher_low = curr_min_low > prev_min_low
    lower_high = curr_max_high < prev_max_high
    lower_low = curr_min_low < prev_min_low

    return pd.DataFrame({
        "higher_high": higher_high,
        "higher_low": higher_low,
        "lower_high": lower_high,
        "lower_low": lower_low,
    })


def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input df must have columns: trade_date, open, high, low, close, volume
    Sorted ascending by trade_date.
    Returns df with all indicator columns added.
    """
    df = df.sort_values("trade_date").reset_index(drop=True)

    df["ema20"] = calculate_ema(df["close"], 20)
    df["ema50"] = calculate_ema(df["close"], 50)

    # ema200 only valid when enough data
    ema200 = calculate_ema(df["close"], 200)
    df["ema200"] = ema200.where(df.index >= 199, other=None)

    df["rsi14"] = calculate_rsi(df["close"])

    adx_df = calculate_adx(df["high"], df["low"], df["close"])
    df["adx14"] = adx_df["adx14"]
    df["plus_di"] = adx_df["plus_di"]
    df["minus_di"] = adx_df["minus_di"]

    df["atr14"] = calculate_atr(df["high"], df["low"], df["close"])

    vol_df = calculate_volume_ratio(df["volume"])
    df["avg_volume20"] = vol_df["avg_volume20"]
    df["volume_ratio"] = vol_df["volume_ratio"]

    struct_df = calculate_price_structure(df["high"], df["low"])
    df["higher_high"] = struct_df["higher_high"]
    df["higher_low"] = struct_df["higher_low"]
    df["lower_high"] = struct_df["lower_high"]
    df["lower_low"] = struct_df["lower_low"]

    return df
