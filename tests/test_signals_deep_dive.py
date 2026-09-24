import numpy as np
import pandas as pd

from stock_advisor.fundamentals import Fundamentals
from stock_advisor.indicators import compute_all
from stock_advisor.news import NewsItem
from stock_advisor.sector import SectorComparison
from stock_advisor.signals import evaluate


def _flat_df(n=250, price=100.0):
    close = np.full(n, price)
    return pd.DataFrame({"Open": close, "High": close + 0.5, "Low": close - 0.5, "Close": close})


def test_strong_fundamentals_and_news_can_push_to_buy():
    df = compute_all(_flat_df())
    price = float(df["Close"].iloc[-1])
    fundamentals = Fundamentals(
        sector="Technology",
        profit_margin=0.25,
        revenue_growth=0.20,
        pe_trailing=30,
        pe_forward=20,
        recommendation_key="buy",
        num_analyst_opinions=15,
        target_mean_price=price * 1.2,
    )
    news = [NewsItem("Company beats and raises guidance", "Reuters", None, "http://x", sentiment=2)]
    sector_comparison = SectorComparison("Technology", "XLK", 2.0, 10.0, outperforming=True)

    sig = evaluate(
        "TEST",
        df,
        fundamentals=fundamentals,
        news=news,
        sector_comparison=sector_comparison,
    )
    assert sig.rating == "BUY"
    assert any("profit margin" in r.lower() for r in sig.reasons)
    assert any("analyst" in r.lower() for r in sig.reasons)


def test_weak_fundamentals_and_news_can_push_to_sell():
    df = compute_all(_flat_df())
    price = float(df["Close"].iloc[-1])
    fundamentals = Fundamentals(
        sector="Energy",
        profit_margin=-0.05,
        revenue_growth=-0.10,
        pe_trailing=60,
        recommendation_key="sell",
        num_analyst_opinions=8,
        target_mean_price=price * 0.7,
    )
    news = [NewsItem("Company misses and faces lawsuit and probe", "Reuters", None, "http://x", sentiment=-3)]
    sector_comparison = SectorComparison("Energy", "XLE", 5.0, -8.0, outperforming=False)

    sig = evaluate(
        "TEST",
        df,
        fundamentals=fundamentals,
        news=news,
        sector_comparison=sector_comparison,
    )
    assert sig.rating == "SELL"


def test_no_optional_data_falls_back_gracefully():
    df = compute_all(_flat_df())
    sig = evaluate("TEST", df)
    assert sig.rating in {"BUY", "SELL", "HOLD"}
    assert sig.fundamentals is None
    assert sig.news == []
