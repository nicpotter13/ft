"""Render a list of Signals (plus macro context) as a self-contained, styled HTML report."""
from __future__ import annotations

import html
from datetime import datetime

from .macro import MacroPoint
from .signals import Signal

_COLORS = {
    "BUY": "#1a7f37",
    "SELL": "#cf222e",
    "HOLD": "#9a6700",
}

_BG = {
    "BUY": "#dafbe1",
    "SELL": "#ffebe9",
    "HOLD": "#fff8c5",
}

_CARD_TEMPLATE = """
<div class="card" style="border-left: 6px solid {color};">
  <div class="card-head">
    <span class="symbol">{symbol}</span>
    <span class="rating" style="background:{bg}; color:{color};">{rating}</span>
  </div>
  <div class="price">Current price: {price}{sector}</div>
  {pl_line}
  {levels}
  <div class="section-label">Why</div>
  <ul class="reasons">
    {reasons}
  </ul>
  {fundamentals_table}
  {news_block}
</div>
"""


def _fmt_pct(x) -> str:
    return f"{x*100:.1f}%" if x is not None else "n/a"


def _fmt_num(x) -> str:
    return f"{x:.2f}" if x is not None else "n/a"


def _fmt_market_cap(x) -> str:
    if x is None:
        return "n/a"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if x >= div:
            return f"{x/div:.1f}{unit}"
    return str(x)


def _fundamentals_html(sig: Signal) -> str:
    f = sig.fundamentals
    if f is None:
        return ""
    rows = [
        ("Market cap", _fmt_market_cap(f.market_cap)),
        ("Trailing P/E", _fmt_num(f.pe_trailing)),
        ("Forward P/E", _fmt_num(f.pe_forward)),
        ("Dividend yield", _fmt_pct(f.dividend_yield)),
        ("Profit margin", _fmt_pct(f.profit_margin)),
        ("Revenue growth (YoY)", _fmt_pct(f.revenue_growth)),
    ]
    if f.target_mean_price:
        rows.append(
            (
                "Analyst target (mean)",
                f"{f.target_mean_price:.2f} (range {_fmt_num(f.target_low_price)}"
                f"-{_fmt_num(f.target_high_price)}, {f.num_analyst_opinions or '?'} analysts)",
            )
        )
    if f.recommendation_key:
        rows.append(("Analyst consensus", f.recommendation_key.replace("_", " ").title()))
    if sig.sector_comparison and sig.sector_comparison.etf_change_pct_3m is not None:
        sc = sig.sector_comparison
        rows.append(
            (
                "vs. sector (3mo)",
                f"{sc.stock_change_pct_3m:+.1f}% vs {sc.etf_symbol} {sc.etf_change_pct_3m:+.1f}%",
            )
        )

    cells = "".join(
        f'<div class="fund-row"><span>{html.escape(k)}</span><b>{html.escape(str(v))}</b></div>'
        for k, v in rows
    )
    return f'<div class="section-label">Fundamentals &amp; analysts</div><div class="fund-grid">{cells}</div>'


def _news_html(sig: Signal) -> str:
    if not sig.news:
        return ""
    items = []
    for item in sig.news:
        tag_color = "#1a7f37" if item.sentiment > 0 else "#cf222e" if item.sentiment < 0 else "#57606a"
        date_str = item.published.strftime("%Y-%m-%d") if item.published else ""
        safe_title = html.escape(item.title)
        safe_link = html.escape(item.link or "#")
        items.append(
            f'<li><a href="{safe_link}" target="_blank" rel="noopener">{safe_title}</a> '
            f'<span style="color:{tag_color}">[{item.sentiment:+d}]</span> '
            f'<span class="news-meta">{html.escape(item.publisher)} {date_str}</span></li>'
        )
    return f'<div class="section-label">Recent headlines (keyword sentiment, not real NLP)</div><ul class="news">{"".join(items)}</ul>'


def _levels_html(sig: Signal) -> str:
    rows = []
    if sig.suggested_buy_below is not None and sig.rating == "BUY":
        rows.append(f"<div>Consider buying at/below: <b>{sig.suggested_buy_below}</b></div>")
    if sig.suggested_stop_loss is not None:
        rows.append(f"<div>Suggested stop-loss: <b>{sig.suggested_stop_loss}</b></div>")
    if sig.suggested_take_profit is not None:
        rows.append(f"<div>Suggested take-profit: <b>{sig.suggested_take_profit}</b></div>")
    if not rows:
        return ""
    return f'<div class="levels">{"".join(rows)}</div>'


def _pl_html(sig: Signal) -> str:
    if sig.unrealized_pct is None:
        return ""
    sign = "+" if sig.unrealized_pct >= 0 else ""
    color = "#1a7f37" if sig.unrealized_pct >= 0 else "#cf222e"
    return f'<div class="pl" style="color:{color}">Unrealized P/L: {sign}{sig.unrealized_pct}%</div>'


def _macro_html(macro: list[MacroPoint]) -> str:
    if not macro:
        return ""
    cells = []
    for point in macro:
        if point.latest is None:
            cells.append(f'<div class="macro-cell"><span>{html.escape(point.label)}</span><b>n/a</b></div>')
            continue
        change = f" ({point.change_pct_1m:+.1f}% / 1mo)" if point.change_pct_1m is not None else ""
        cells.append(
            f'<div class="macro-cell"><span>{html.escape(point.label)}</span>'
            f"<b>{point.latest}{change}</b></div>"
        )
    return f'<div class="macro"><div class="section-label" style="margin-top:0;">Market backdrop</div><div class="macro-grid">{"".join(cells)}</div></div>'


def render(signals: list[Signal], macro: list[MacroPoint], generated_at: datetime) -> str:
    order = {"BUY": 0, "SELL": 1, "HOLD": 2}
    cards = []
    for sig in sorted(signals, key=lambda s: order.get(s.rating, 9)):
        reasons_html = "\n    ".join(f"<li>{html.escape(r)}</li>" for r in sig.reasons)
        sector_str = ""
        if sig.fundamentals and sig.fundamentals.sector:
            sector_str = f" &middot; {html.escape(sig.fundamentals.sector)}"
        cards.append(
            _CARD_TEMPLATE.format(
                color=_COLORS.get(sig.rating, "#57606a"),
                bg=_BG.get(sig.rating, "#eaeef2"),
                symbol=html.escape(sig.symbol),
                rating=html.escape(sig.rating),
                price=sig.price,
                sector=sector_str,
                pl_line=_pl_html(sig),
                levels=_levels_html(sig),
                reasons=reasons_html,
                fundamentals_table=_fundamentals_html(sig),
                news_block=_news_html(sig),
            )
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stock Signal Report</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: #f6f8fa;
    color: #1f2328;
    margin: 0;
    padding: 24px;
  }}
  .container {{ max-width: 820px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .timestamp {{ color: #57606a; font-size: 13px; margin-bottom: 16px; }}
  .macro {{
    background: white;
    border-radius: 8px;
    padding: 14px 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  .macro-grid {{ display: flex; gap: 24px; flex-wrap: wrap; }}
  .macro-cell {{ display: flex; flex-direction: column; font-size: 13.5px; }}
  .macro-cell span {{ color: #57606a; margin-bottom: 2px; }}
  .card {{
    background: white;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  .card-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}
  .symbol {{ font-size: 18px; font-weight: 600; }}
  .rating {{
    font-weight: 700;
    font-size: 13px;
    padding: 4px 10px;
    border-radius: 999px;
    letter-spacing: 0.03em;
  }}
  .price {{ color: #57606a; font-size: 14px; margin-bottom: 4px; }}
  .pl {{ font-size: 14px; font-weight: 600; margin-bottom: 4px; }}
  .levels {{ font-size: 14px; margin: 8px 0; color: #1f2328; }}
  .levels div {{ margin-bottom: 2px; }}
  .section-label {{
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #8c959f;
    margin-top: 14px;
    margin-bottom: 6px;
    font-weight: 600;
  }}
  .reasons {{ margin: 0; padding-left: 18px; font-size: 13.5px; color: #424a53; }}
  .reasons li {{ margin-bottom: 3px; }}
  .fund-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 16px;
  }}
  .fund-row {{
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    border-bottom: 1px solid #eaeef2;
    padding-bottom: 3px;
  }}
  .fund-row span {{ color: #57606a; }}
  .news {{ list-style: none; margin: 0; padding: 0; font-size: 13px; }}
  .news li {{ margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #eaeef2; }}
  .news a {{ color: #0969da; text-decoration: none; }}
  .news a:hover {{ text-decoration: underline; }}
  .news-meta {{ color: #8c959f; font-size: 12px; }}
  .disclaimer {{
    margin-top: 24px;
    padding: 14px 16px;
    background: #fff8c5;
    border-radius: 8px;
    font-size: 12.5px;
    color: #57606a;
    line-height: 1.5;
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Stock Signal Report</h1>
  <div class="timestamp">Generated {generated_at.strftime('%Y-%m-%d %H:%M UTC')}</div>
  {_macro_html(macro)}
  {"".join(cards)}
  <div class="disclaimer">
    <b>Not financial advice.</b> Ratings combine technical indicators (moving
    averages, RSI, MACD, ATR), basic fundamentals and analyst price targets,
    a keyword-based read of recent headlines (not real sentiment analysis),
    and a comparison to the stock's sector ETF - all from free, delayed
    Yahoo Finance data. No macroeconomic or geopolitical judgement is baked
    into any single stock's rating; the market backdrop above is shown for
    context only. Data can be wrong, delayed, or missing. Always do your own
    research and consider a licensed financial advisor before trading.
  </div>
</div>
</body>
</html>
"""
