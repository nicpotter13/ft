"""CLI entry point: scan a watchlist and print/save a buy/sell/hold report."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from .data import fetch_history
from .indicators import compute_all
from .signals import Signal, evaluate
from .watchlist import load_watchlist

DISCLAIMER = (
    "DISCLAIMER: This tool generates signals from basic technical indicators "
    "(moving averages, RSI, MACD, ATR) on delayed Yahoo Finance data. It is NOT "
    "financial advice. Data can be wrong, delayed, or missing. Always do your "
    "own research and consider consulting a licensed financial advisor before "
    "trading."
)


def format_report(signals: list[Signal], generated_at: datetime) -> str:
    lines = []
    lines.append(f"Stock signal report - {generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)
    lines.append("")

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
        for reason in sig.reasons:
            lines.append(f"           - {reason}")
        lines.append("")

    lines.append(DISCLAIMER)
    return "\n".join(lines)


def run(watchlist_path: str, output_path: str | None) -> int:
    entries = load_watchlist(watchlist_path)
    if not entries:
        print(f"No tickers found in {watchlist_path}", file=sys.stderr)
        return 1

    signals: list[Signal] = []
    for entry in entries:
        symbol = entry["symbol"]
        try:
            history = fetch_history(symbol)
            with_indicators = compute_all(history)
            signals.append(evaluate(symbol, with_indicators, holding=entry["holding"]))
        except Exception as exc:  # noqa: BLE001 - report and continue with other tickers
            print(f"Skipping {symbol}: {exc}", file=sys.stderr)

    if not signals:
        print("No signals could be generated.", file=sys.stderr)
        return 1

    report = format_report(signals, datetime.now(timezone.utc))
    print(report)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        print(f"\nSaved report to {output_path}", file=sys.stderr)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a watchlist and print buy/sell/hold signals from technical indicators."
    )
    parser.add_argument(
        "-w", "--watchlist", default="watchlist.yaml", help="Path to watchlist YAML file"
    )
    parser.add_argument("-o", "--output", default=None, help="Optional path to save the report to")
    args = parser.parse_args()

    sys.exit(run(args.watchlist, args.output))


if __name__ == "__main__":
    main()
