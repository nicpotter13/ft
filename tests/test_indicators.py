import numpy as np
import pandas as pd

from stock_advisor.indicators import compute_all, rsi, sma


def _fake_ohlcv(n=250, start=100.0, trend=0.2, seed=0):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, n)
    close = start + np.cumsum(trend + noise * 0.3)
    close = np.maximum(close, 1.0)
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close})


def test_sma_matches_manual_mean():
    close = pd.Series([1, 2, 3, 4, 5], dtype=float)
    result = sma(close, 3)
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == 2.0
    assert result.iloc[4] == 4.0


def test_rsi_bounds():
    df = _fake_ohlcv()
    result = rsi(df["Close"], 14)
    valid = result.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_rsi_strong_uptrend_is_high():
    close = pd.Series(np.arange(1, 60, dtype=float))
    result = rsi(close, 14)
    assert result.iloc[-1] > 90


def test_compute_all_adds_expected_columns():
    df = _fake_ohlcv()
    out = compute_all(df)
    for col in ["sma50", "sma200", "rsi14", "macd", "macd_signal", "macd_hist", "atr14"]:
        assert col in out.columns
    assert len(out) == len(df)
