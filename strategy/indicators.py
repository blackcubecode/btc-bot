"""Indicator teknikal � pure pandas/numpy, tanpa API."""
from __future__ import annotations
import pandas as pd
import numpy as np
import config


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tambah semua indikator ke DataFrame.

    Input: df dengan kolom [open, high, low, close, volume], index waktu.
    Output: df + kolom indicator.
    """
    df = df.copy()

    # ===== ATR =====
    high, low, close = df["high"], df["low"], df["close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = tr.rolling(config.ATR_PERIOD).mean()

    # ===== RSI =====
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(config.RSI_PERIOD).mean()
    avg_loss = loss.rolling(config.RSI_PERIOD).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)

    # ===== Bollinger Bands =====
    sma = close.rolling(config.BB_PERIOD).mean()
    std = close.rolling(config.BB_PERIOD).std()
    df["bb_mid"] = sma
    df["bb_upper"] = sma + config.BB_STD * std
    df["bb_lower"] = sma - config.BB_STD * std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / sma
    df["bb_position"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)

    # ===== ADX =====
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr_raw = tr.rolling(config.ADX_PERIOD).mean()
    plus_di = 100 * (plus_dm.rolling(config.ADX_PERIOD).mean() / atr_raw.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(config.ADX_PERIOD).mean() / atr_raw.replace(0, np.nan))
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    df["adx"] = dx.rolling(config.ADX_PERIOD).mean()
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di

    # ===== EMA trend =====
    df["ema_fast"] = close.ewm(span=20, adjust=False).mean()
    df["ema_slow"] = close.ewm(span=50, adjust=False).mean()

    # ===== Volume =====
    df["vol_sma"] = df["volume"].rolling(20).mean()

    return df


def last_candle(df: pd.DataFrame) -> dict:
    """Ambil candle terakhir sebagai dict."""
    return df.iloc[-1].to_dict()


# ===== Self-test =====
if __name__ == "__main__":
    # Generate fake data untuk test
    np.random.seed(42)
    n = 200
    price = 78000 + np.cumsum(np.random.randn(n) * 100)
    df = pd.DataFrame({
        "open": price + np.random.randn(n) * 50,
        "high": price + np.abs(np.random.randn(n)) * 200,
        "low": price - np.abs(np.random.randn(n)) * 200,
        "close": price,
        "volume": np.random.rand(n) * 100,
    })
    df.index = pd.date_range("2024-01-01", periods=n, freq="1h")

    df = add_indicators(df)
    print("? add_indicators OK")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    print(f"\nLast row:")
    print(df.iloc[-1][["close", "atr", "rsi", "bb_position", "adx", "ema_fast", "ema_slow"]])
