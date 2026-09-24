# Stock Advisor

A command-line tool that watches a list of stocks, computes technical
indicators (moving averages, RSI, MACD, ATR-based volatility), and prints a
BUY / SELL / HOLD signal for each one, with a reasoned explanation and
suggested price levels.

If you tell it what you paid for a stock you already hold, it will also
flag when to sell based on a stop-loss and take-profit percentage.

**This is not financial advice.** It's a rules-based heuristic over free,
delayed (15-20 min) Yahoo Finance data. Use it as one input among many.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure your watchlist

Edit `watchlist.yaml`:

```yaml
tickers:
  - symbol: AAPL          # just watch it, no signal personalization
  - symbol: MSFT
  - symbol: VOD.L         # a stock you already own
    holding:
      shares: 100
      cost_basis: 72.50   # price you paid; used for stop-loss/take-profit
```

Symbols use Yahoo Finance tickers (e.g. `AAPL`, `MSFT`, `VOD.L` for London,
`7203.T` for Tokyo, `BMW.DE` for Frankfurt).

## Run it

```bash
python -m stock_advisor.cli -w watchlist.yaml
```

Save the report to a file too:

```bash
python -m stock_advisor.cli -w watchlist.yaml -o report.txt
```

Example output:

```
AAPL       BUY   price=227.5
           consider buying at/below: 224.10
           suggested stop-loss: 218.30
           - 50-day average above 200-day average (uptrend / golden cross)
           - RSI 45 is neutral
           - MACD above its signal line (bullish momentum)

VOD.L      SELL  price=65.20
           unrealized P/L: -10.07%
           suggested stop-loss: 66.70
           - Price 65.20 has hit your stop-loss level 66.70 (-8% from cost basis 72.50)
```

## How the signal is decided

For stocks you're just watching (no `holding`):
- **BUY** when the trend, RSI, and MACD line up bullish (at least 2 of 3
  signals agree: 50-day SMA > 200-day SMA, RSI not overbought, MACD above
  its signal line).
- **SELL** when they line up bearish.
- **HOLD** otherwise.

For stocks you hold (with `cost_basis` set):
- **SELL** if the price drops to your stop-loss (default 8% below cost
  basis), rises to your take-profit target (default 20% above cost basis),
  or multiple bearish signals stack up.
- Otherwise **HOLD**.

Tune `stop_loss_pct` / `take_profit_pct` by editing the call to `evaluate()`
in `stock_advisor/cli.py`, or extend the CLI to accept them as flags.

## Scheduling

Run it daily with cron, e.g. after US market close:

```
0 21 * * 1-5 cd /path/to/ft && .venv/bin/python -m stock_advisor.cli -o report.txt
```

## Tests

```bash
pytest tests/
```

The indicator and signal logic is covered by unit tests using synthetic
price data, so it runs without network access. The `data.py` module
(actual Yahoo Finance fetch) requires outbound network access to
`*.yahoo.com`, which some sandboxed environments block.
