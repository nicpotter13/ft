"""Fundamentals, valuation, and analyst-forecast data from Yahoo Finance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import yfinance as yf


@dataclass
class Fundamentals:
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_trailing: Optional[float] = None
    pe_forward: Optional[float] = None
    dividend_yield: Optional[float] = None
    profit_margin: Optional[float] = None
    revenue_growth: Optional[float] = None
    target_mean_price: Optional[float] = None
    target_high_price: Optional[float] = None
    target_low_price: Optional[float] = None
    recommendation_key: Optional[str] = None
    num_analyst_opinions: Optional[int] = None


def fetch_fundamentals(symbol: str) -> Fundamentals:
    """Best-effort fetch; any missing field is left as None rather than raising."""
    try:
        info = yf.Ticker(symbol).get_info()
    except Exception:
        info = {}

    return Fundamentals(
        sector=info.get("sector"),
        industry=info.get("industry"),
        market_cap=info.get("marketCap"),
        pe_trailing=info.get("trailingPE"),
        pe_forward=info.get("forwardPE"),
        dividend_yield=info.get("dividendYield"),
        profit_margin=info.get("profitMargins"),
        revenue_growth=info.get("revenueGrowth"),
        target_mean_price=info.get("targetMeanPrice"),
        target_high_price=info.get("targetHighPrice"),
        target_low_price=info.get("targetLowPrice"),
        recommendation_key=info.get("recommendationKey"),
        num_analyst_opinions=info.get("numberOfAnalystOpinions"),
    )
