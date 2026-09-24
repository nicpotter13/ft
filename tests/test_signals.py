import numpy as np
import pandas as pd

from stock_advisor.indicators import compute_all
from stock_advisor.signals import evaluate


def _trending_df(n=250, start=100.0, trend=0.5, seed=1):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, n)
    close = start + np.cumsum(trend + noise * 0.2)
    close = np.maximum(close, 1.0)
    high = close + 0.5
    low = close - 0.5
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close})


def test_uptrend_without_holding_can_be_buy():
    df = compute_all(_trending_df(trend=0.8))
    sig = evaluate("TEST", df)
    assert sig.rating in {"BUY", "HOLD"}
    assert sig.price > 0


def test_holding_stop_loss_triggers_sell():
    df = compute_all(_trending_df(trend=-0.8, seed=2))
    last_price = float(df["Close"].iloc[-1])
    holding = {"shares": 10, "cost_basis": last_price * 2}  # price has fallen 50%
    sig = evaluate("TEST", df, holding=holding, stop_loss_pct=0.08)
    assert sig.rating == "SELL"
    assert any("stop-loss" in r for r in sig.reasons)


def test_holding_take_profit_triggers_sell():
    df = compute_all(_trending_df(trend=0.8, seed=3))
    last_price = float(df["Close"].iloc[-1])
    holding = {"shares": 10, "cost_basis": last_price / 2}  # price has doubled
    sig = evaluate("TEST", df, holding=holding, take_profit_pct=0.20)
    assert sig.rating == "SELL"
    assert any("take-profit" in r for r in sig.reasons)
    assert sig.unrealized_pct > 0
