"""General macroeconomic backdrop: a handful of widely-watched market indices.

This is deliberately shallow (three indices, no interpretation model) - it
gives you the numbers a professional would glance at, not a macro forecast.
Fetched once per run and shown as shared context, not folded into any single
stock's score, since attributing a market-wide number to one company is not
sound.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import yfinance as yf

_INDICATORS = {
    "^TNX": "10-Year US Treasury Yield",
    "^VIX": "CBOE Volatility Index (VIX)",
    "DX-Y.NYB": "US Dollar Index",
}


@dataclass
class MacroPoint:
    label: str
    symbol: str
    latest: Optional[float]
    change_pct_1m: Optional[float]


def fetch_macro_context() -> list[MacroPoint]:
    points = []
    for symbol, label in _INDICATORS.items():
        try:
            hist = yf.Ticker(symbol).history(period="2mo", interval="1d")
            if hist.empty:
                points.append(MacroPoint(label, symbol, None, None))
                continue
            latest = float(hist["Close"].iloc[-1])
            month_ago_idx = max(0, len(hist) - 22)
            month_ago = float(hist["Close"].iloc[month_ago_idx])
            change_pct = round((latest - month_ago) / month_ago * 100, 2) if month_ago else None
            points.append(MacroPoint(label, symbol, round(latest, 2), change_pct))
        except Exception:
            points.append(MacroPoint(label, symbol, None, None))
    return points
