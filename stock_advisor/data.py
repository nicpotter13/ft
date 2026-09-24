"""Market data fetching via Yahoo Finance (yfinance). Data is delayed ~15-20 min."""
from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV history for a symbol. Raises ValueError if no data is returned."""
    df = yf.Ticker(symbol).history(period=period, interval=interval)
    if df is None or df.empty:
        raise ValueError(f"No data returned for symbol '{symbol}' - check the ticker is valid")
    return df
