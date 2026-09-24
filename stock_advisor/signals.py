"""Turn indicator values, fundamentals, news, and sector data into a
plain-English signal and suggested price levels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .fundamentals import Fundamentals
from .news import NewsItem
from .sector import SectorComparison

_BULLISH_RECS = {"buy", "strong_buy"}
_BEARISH_RECS = {"sell", "strong_sell"}


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
    fundamentals: Optional[Fundamentals] = None
    news: list[NewsItem] = field(default_factory=list)
    sector_comparison: Optional[SectorComparison] = None


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


def _fundamental_reasons(f: Optional[Fundamentals], price: float) -> tuple[list[str], int]:
    reasons: list[str] = []
    score = 0
    if f is None:
        return reasons, score

    if f.profit_margin is not None:
        if f.profit_margin < 0:
            reasons.append(f"Negative profit margin ({f.profit_margin*100:.1f}%)")
            score -= 1
        elif f.profit_margin > 0.15:
            reasons.append(f"Healthy profit margin ({f.profit_margin*100:.1f}%)")
            score += 1

    if f.revenue_growth is not None:
        if f.revenue_growth < 0:
            reasons.append(f"Revenue shrinking year-over-year ({f.revenue_growth*100:.1f}%)")
            score -= 1
        elif f.revenue_growth > 0.10:
            reasons.append(f"Revenue growing year-over-year (+{f.revenue_growth*100:.1f}%)")
            score += 1

    if f.pe_trailing is not None and f.pe_forward is not None and f.pe_trailing > 0:
        if f.pe_forward < f.pe_trailing:
            reasons.append(
                f"Forward P/E ({f.pe_forward:.1f}) below trailing P/E ({f.pe_trailing:.1f}) "
                "- earnings expected to grow"
            )
            score += 1
        elif f.pe_forward > f.pe_trailing * 1.15:
            reasons.append(
                f"Forward P/E ({f.pe_forward:.1f}) above trailing P/E ({f.pe_trailing:.1f}) "
                "- earnings expected to shrink"
            )
            score -= 1

    if f.pe_trailing is not None and f.pe_trailing > 50:
        reasons.append(f"Trailing P/E of {f.pe_trailing:.1f} is rich vs. the broad market")

    if f.recommendation_key:
        key = f.recommendation_key.lower()
        if key in _BULLISH_RECS:
            reasons.append(f"Analyst consensus: {f.recommendation_key} ({f.num_analyst_opinions or '?'} analysts)")
            score += 1
        elif key in _BEARISH_RECS:
            reasons.append(f"Analyst consensus: {f.recommendation_key} ({f.num_analyst_opinions or '?'} analysts)")
            score -= 1

    if f.target_mean_price:
        upside_pct = (f.target_mean_price - price) / price * 100
        if upside_pct >= 10:
            reasons.append(
                f"Analyst mean target {f.target_mean_price:.2f} implies +{upside_pct:.0f}% upside"
            )
            score += 1
        elif upside_pct <= -10:
            reasons.append(
                f"Analyst mean target {f.target_mean_price:.2f} implies {upside_pct:.0f}% downside"
            )
            score -= 1

    return reasons, score


def _news_reasons(news: list[NewsItem]) -> tuple[list[str], int]:
    reasons: list[str] = []
    if not news:
        return reasons, 0
    total = sum(item.sentiment for item in news)
    if total >= 2:
        reasons.append(f"Recent headlines skew positive (net keyword score +{total} across {len(news)} articles)")
        return reasons, 1
    if total <= -2:
        reasons.append(f"Recent headlines skew negative (net keyword score {total} across {len(news)} articles)")
        return reasons, -1
    reasons.append(f"Recent headlines are mixed/neutral (net keyword score {total:+d} across {len(news)} articles)")
    return reasons, 0


def _sector_reasons(sc: Optional[SectorComparison]) -> tuple[list[str], int]:
    reasons: list[str] = []
    score = 0
    if sc is None or sc.outperforming is None:
        return reasons, score
    if sc.outperforming:
        reasons.append(
            f"Outperforming its sector over 3 months ({sc.stock_change_pct_3m:+.1f}% vs "
            f"{sc.etf_symbol} {sc.etf_change_pct_3m:+.1f}%)"
        )
        score += 1
    else:
        reasons.append(
            f"Underperforming its sector over 3 months ({sc.stock_change_pct_3m:+.1f}% vs "
            f"{sc.etf_symbol} {sc.etf_change_pct_3m:+.1f}%)"
        )
        score -= 1
    return reasons, score


def evaluate(
    symbol: str,
    df_with_indicators: pd.DataFrame,
    holding: Optional[dict] = None,
    stop_loss_pct: float = 0.08,
    take_profit_pct: float = 0.20,
    fundamentals: Optional[Fundamentals] = None,
    news: Optional[list[NewsItem]] = None,
    sector_comparison: Optional[SectorComparison] = None,
) -> Signal:
    """Evaluate the most recent row of indicator data - plus fundamentals,
    analyst targets, recent news, and sector performance, when supplied -
    and produce a Signal.

    `holding`, if given, is {"shares": float, "cost_basis": float} for a
    position you already own; this adds a personal stop-loss/take-profit.
    """
    news = news or []
    latest = df_with_indicators.iloc[-1]
    price = float(latest["Close"])

    reasons, score = _trend_reasons(latest)
    f_reasons, f_score = _fundamental_reasons(fundamentals, price)
    n_reasons, n_score = _news_reasons(news)
    s_reasons, s_score = _sector_reasons(sector_comparison)
    reasons += f_reasons + n_reasons + s_reasons
    score += f_score + n_score + s_score

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

    # BUY/SELL threshold is wider than a pure-technical read (was +/-2)
    # because up to ~4x as many independent factors now feed the score.
    buy_threshold, sell_threshold = 4, -4

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
        elif score <= sell_threshold:
            rating = "SELL"
            reasons.append("Multiple bearish signals across trend, fundamentals, news and sector suggest trimming")
        else:
            rating = "HOLD"
    else:
        if score >= buy_threshold:
            rating = "BUY"
        elif score <= sell_threshold:
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
        fundamentals=fundamentals,
        news=news,
        sector_comparison=sector_comparison,
    )
