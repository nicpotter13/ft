"""Compare a stock's recent return against its sector's SPDR ETF, as a
rough stand-in for 'is this outperforming its peers'."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import yfinance as yf

SECTOR_ETF = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Consumer Defensive": "XLP",
    "Consumer Cyclical": "XLY",
    "Industrials": "XLI",
    "Utilities": "XLU",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

_etf_cache: dict[str, Optional[float]] = {}


@dataclass
class SectorComparison:
    sector: str
    etf_symbol: str
    etf_change_pct_3m: Optional[float]
    stock_change_pct_3m: Optional[float]
    outperforming: Optional[bool]


def _etf_3m_change(etf_symbol: str) -> Optional[float]:
    if etf_symbol in _etf_cache:
        return _etf_cache[etf_symbol]
    try:
        hist = yf.Ticker(etf_symbol).history(period="3mo", interval="1d")
        if hist.empty:
            _etf_cache[etf_symbol] = None
        else:
            start, end = float(hist["Close"].iloc[0]), float(hist["Close"].iloc[-1])
            _etf_cache[etf_symbol] = round((end - start) / start * 100, 2)
    except Exception:
        _etf_cache[etf_symbol] = None
    return _etf_cache[etf_symbol]


def compare_to_sector(sector: Optional[str], stock_change_pct_3m: Optional[float]) -> Optional[SectorComparison]:
    if not sector or sector not in SECTOR_ETF:
        return None
    etf_symbol = SECTOR_ETF[sector]
    etf_change = _etf_3m_change(etf_symbol)
    outperforming = None
    if etf_change is not None and stock_change_pct_3m is not None:
        outperforming = stock_change_pct_3m > etf_change
    return SectorComparison(
        sector=sector,
        etf_symbol=etf_symbol,
        etf_change_pct_3m=etf_change,
        stock_change_pct_3m=stock_change_pct_3m,
        outperforming=outperforming,
    )
