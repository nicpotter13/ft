"""Turn indicator values into a plain-English signal and suggested price levels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class Signal:
    symbol: str
    price: float
    rating: str  # BUY / SELL / HOLD
    reasons: list[str] = field(default_factory=list)
    suggested_buy_below: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    unrealized_pct: Optional[float] = None


def _trend_reasons(latest: pd.Series) -> tuple[list[str], int]:
    """Return (reasons, score) where score > 0 is bullish, < 0 bearish."""
    reasons: list[str] = []
    score = 0

    sma50, sma200 = latest.get("sma50"), latest.get("sma200")
    if pd.notna(sma50) and pd.notna(sma200):
        if sma50 > sma200:
            reasons.append("50-day average above 200-day average (uptrend / golden cross)")
            score += 1
        else:
            reasons.append("50-day average below 200-day average (downtrend / death cross)")
            score -= 1

    rsi14 = latest.get("rsi14")
    if pd.notna(rsi14):
        if rsi14 >= 70:
            reasons.append(f"RSI {rsi14:.0f} is overbought (>=70)")
            score -= 1
        elif rsi14 <= 30:
            reasons.append(f"RSI {rsi14:.0f} is oversold (<=30)")
            score += 1

    macd_line, macd_signal = latest.get("macd"), latest.get("macd_signal")
    if pd.notna(macd_line) and pd.notna(macd_signal):
        if macd_line > macd_signal:
            reasons.append("MACD above its signal line (bullish momentum)")
            score += 1
        else:
            reasons.append("MACD below its signal line (bearish momentum)")
            score -= 1

    return reasons, score


def evaluate(
    symbol: str,
    df_with_indicators: pd.DataFrame,
    holding: Optional[dict] = None,
    stop_loss_pct: float = 0.08,
    take_profit_pct: float = 0.20,
) -> Signal:
    """Evaluate the most recent row of indicator data and produce a Signal.

    `holding`, if given, is {"shares": float, "cost_basis": float} for a
    position you already own; this adds a personal stop-loss/take-profit.
    """
    latest = df_with_indicators.iloc[-1]
    price = float(latest["Close"])

    reasons, score = _trend_reasons(latest)

    atr14 = latest.get("atr14")
    suggested_buy_below = None
    suggested_stop_loss = None
    if pd.notna(latest.get("sma50")):
        suggested_buy_below = round(float(latest["sma50"]), 2)
    if pd.notna(atr14):
        suggested_stop_loss = round(price - 2 * float(atr14), 2)

    rating = "HOLD"
    unrealized_pct = None
    suggested_take_profit = None

    if holding:
        cost_basis = float(holding["cost_basis"])
        unrealized_pct = round((price - cost_basis) / cost_basis * 100, 2)
        personal_stop = round(cost_basis * (1 - stop_loss_pct), 2)
        personal_target = round(cost_basis * (1 + take_profit_pct), 2)
        suggested_stop_loss = max(suggested_stop_loss or 0, personal_stop)
        suggested_take_profit = personal_target

        if price <= personal_stop:
            rating = "SELL"
            reasons.append(
                f"Price {price:.2f} has hit your stop-loss level {personal_stop:.2f} "
                f"({-stop_loss_pct*100:.0f}% from cost basis {cost_basis:.2f})"
            )
        elif price >= personal_target:
            rating = "SELL"
            reasons.append(
                f"Price {price:.2f} has reached your take-profit target {personal_target:.2f} "
                f"(+{take_profit_pct*100:.0f}% from cost basis {cost_basis:.2f})"
            )
        elif score <= -2:
            rating = "SELL"
            reasons.append("Multiple bearish signals suggest trimming the position")
        else:
            rating = "HOLD"
    else:
        if score >= 2:
            rating = "BUY"
        elif score <= -2:
            rating = "SELL"
        else:
            rating = "HOLD"

    return Signal(
        symbol=symbol,
        price=round(price, 2),
        rating=rating,
        reasons=reasons,
        suggested_buy_below=suggested_buy_below,
        suggested_stop_loss=suggested_stop_loss,
        suggested_take_profit=suggested_take_profit,
        unrealized_pct=unrealized_pct,
    )
