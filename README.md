# Stock Advisor

A command-line tool that watches a list of stocks and produces a
BUY / SELL / HOLD "deep dive" report for each one, combining:

- **Technical indicators** - moving averages, RSI, MACD, ATR-based volatility
- **Fundamentals & valuation** - P/E (trailing/forward), profit margin,
  revenue growth, market cap, dividend yield
- **Analyst forecasts** - mean/high/low price targets and consensus rating
- **Recent news** - latest headlines per stock with a keyword-based
  sentiment read (see caveat below)
- **Sector comparison** - how the stock has done vs. its sector's ETF over
  3 months
- **Market backdrop** - 10-year Treasury yield, VIX, and the US Dollar
  Index, shown as shared context (not folded into any single stock's score)

If you tell it what you paid for a stock you already hold, it will also
flag when to sell based on a stop-loss and take-profit percentage.

**This is not financial advice.** Every input above comes from free,
delayed (15-20 min) Yahoo Finance data, combined with fixed, transparent
rules - not judgement, and not a trained model. In particular: the "news
sentiment" is a plain positive/negative keyword count per headline, not
real natural-language understanding, and can easily be wrong (e.g.
sarcasm, negation, or an unusual word choice will fool it). Use this as
one input among many, never as the sole basis for a trade.

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

This fetches, per stock: price history, company fundamentals, analyst
targets, and recent news - plus the market backdrop once per run - so it's
slower than a pure price check (a handful of seconds per stock is normal).

Save the text report to a file too:

```bash
python -m stock_advisor.cli -w watchlist.yaml -o report.txt
```

By default it also writes a styled `report.html` you can open in a browser
tab (color-coded BUY/SELL/HOLD cards, fundamentals table, clickable news
links, no terminal reading required). Change where it's saved with
`--html path/to/file.html`, or skip it with `--html ''`.

## How the signal is decided

Every factor below adds or subtracts points from a single score; the more
of them agree, the stronger the signal.

**Technical** (price-history based):
- 50-day average vs. 200-day average (trend)
- RSI overbought/oversold
- MACD vs. its signal line (momentum)

**Fundamentals & analysts:**
- Profit margin positive/negative and its size
- Revenue growth year-over-year
- Forward P/E vs. trailing P/E (is the market pricing in earnings growth?)
- Analyst consensus rating (buy/hold/sell)
- Upside/downside implied by the analyst mean price target

**News & sector:**
- Net keyword sentiment across recent headlines
- 3-month performance vs. the stock's sector ETF

For stocks you're just watching (no `holding`): **BUY** when the combined
score is strongly positive, **SELL** when strongly negative, **HOLD**
otherwise.

For stocks you hold (with `cost_basis` set): **SELL** if the price hits
your stop-loss (default 8% below cost) or take-profit (default 20% above
cost), or if the combined score turns strongly negative. Otherwise
**HOLD**.

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
data, so it runs without network access. The `data.py`, `fundamentals.py`,
`news.py`, `macro.py`, and `sector.py` modules make live Yahoo Finance
calls and require outbound network access to `*.yahoo.com`, which some
sandboxed environments block.
