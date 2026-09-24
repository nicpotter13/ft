"""CLI entry point: scan a watchlist and print/save a buy/sell/hold report."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from .data import fetch_history
from .fundamentals import fetch_fundamentals
from .html_report import render as render_html
from .indicators import compute_all
from .macro import MacroPoint, fetch_macro_context
from .news import fetch_news
from .sector import compare_to_sector
from .signals import Signal, evaluate
from .watchlist import load_watchlist

DISCLAIMER = (
    "DISCLAIMER: This tool combines technical indicators (moving averages, RSI, "
    "MACD, ATR), basic fundamentals and analyst targets, a keyword-based read of "
    "recent headlines, and a sector comparison - all from free Yahoo Finance data. "
    "It is NOT financial advice and the 'sentiment' score is a simple word count, "
    "not real NLP. Data can be wrong, delayed, or missing. Always do your own "
    "research and consider consulting a licensed financial advisor before trading."
)


def _stock_change_pct_3m(history) -> float | None:
    if len(history) < 2:
        return None
    idx = max(0, len(history) - 63)
    start = float(history["Close"].iloc[idx])
    end = float(history["Close"].iloc[-1])
    if start == 0:
        return None
    return round((end - start) / start * 100, 2)


def format_macro(macro: list[MacroPoint]) -> list[str]:
    lines = ["Market backdrop", "-" * 20]
    for point in macro:
        if point.latest is None:
            lines.append(f"{point.label}: unavailable")
            continue
        change = f" ({point.change_pct_1m:+.1f}% over 1mo)" if point.change_pct_1m is not None else ""
        lines.append(f"{point.label}: {point.latest}{change}")
    lines.append("")
    return lines


def format_report(signals: list[Signal], macro: list[MacroPoint], generated_at: datetime) -> str:
    lines = []
    lines.append(f"Stock signal report - {generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)
    lines.append("")
    lines += format_macro(macro)

    order = {"BUY": 0, "SELL": 1, "HOLD": 2}
    for sig in sorted(signals, key=lambda s: order.get(s.rating, 9)):
        lines.append(f"{sig.symbol:<10} {sig.rating:<5} price={sig.price}")
        if sig.unrealized_pct is not None:
            lines.append(f"           unrealized P/L: {sig.unrealized_pct:+.2f}%")
        if sig.suggested_buy_below is not None and sig.rating == "BUY":
            lines.append(f"           consider buying at/below: {sig.suggested_buy_below}")
        if sig.suggested_stop_loss is not None:
            lines.append(f"           suggested stop-loss: {sig.suggested_stop_loss}")
        if sig.suggested_take_profit is not None:
            lines.append(f"           suggested take-profit: {sig.suggested_take_profit}")
        if sig.fundamentals and sig.fundamentals.sector:
            lines.append(f"           sector: {sig.fundamentals.sector} / {sig.fundamentals.industry}")
        for reason in sig.reasons:
            lines.append(f"           - {reason}")
        for item in sig.news:
            lines.append(f"           news: [{item.sentiment:+d}] {item.title} ({item.publisher})")
        lines.append("")

    lines.append(DISCLAIMER)
    return "\n".join(lines)


def run(watchlist_path: str, output_path: str | None, html_path: str | None) -> int:
    entries = load_watchlist(watchlist_path)
    if not entries:
        print(f"No tickers found in {watchlist_path}", file=sys.stderr)
        return 1

    print("Fetching market backdrop (treasury yield, VIX, dollar index)...", file=sys.stderr)
    macro = fetch_macro_context()

    signals: list[Signal] = []
    for entry in entries:
        symbol = entry["symbol"]
        try:
            print(f"Fetching {symbol}...", file=sys.stderr)
            history = fetch_history(symbol)
            with_indicators = compute_all(history)
            fundamentals = fetch_fundamentals(symbol)
            news = fetch_news(symbol)
            change_3m = _stock_change_pct_3m(history)
            sector_comparison = compare_to_sector(fundamentals.sector, change_3m)
            signals.append(
                evaluate(
                    symbol,
                    with_indicators,
                    holding=entry["holding"],
                    fundamentals=fundamentals,
                    news=news,
                    sector_comparison=sector_comparison,
                )
            )
        except Exception as exc:  # noqa: BLE001 - report and continue with other tickers
            print(f"Skipping {symbol}: {exc}", file=sys.stderr)

    if not signals:
        print("No signals could be generated.", file=sys.stderr)
        return 1

    generated_at = datetime.now(timezone.utc)
    report = format_report(signals, macro, generated_at)
    print(report)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        print(f"\nSaved text report to {output_path}", file=sys.stderr)

    if html_path:
        with open(html_path, "w") as f:
            f.write(render_html(signals, macro, generated_at))
        print(f"Saved HTML report to {html_path}", file=sys.stderr)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a watchlist and produce a buy/sell/hold deep-dive report: "
        "technical indicators, fundamentals, analyst targets, news, sector, and macro context."
    )
    parser.add_argument(
        "-w", "--watchlist", default="watchlist.yaml", help="Path to watchlist YAML file"
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Optional path to save the text report to"
    )
    parser.add_argument(
        "--html",
        default="report.html",
        help="Path to save a styled HTML report to (default: report.html). Pass '' to skip.",
    )
    args = parser.parse_args()

    sys.exit(run(args.watchlist, args.output, args.html or None))


if __name__ == "__main__":
    main()
