"""Loading the watchlist.yaml config file."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


def load_watchlist(path: str | Path) -> list[dict]:
    """Return a list of {"symbol": str, "holding": dict | None} entries."""
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    tickers = data.get("tickers", [])
    entries = []
    for t in tickers:
        if isinstance(t, str):
            entries.append({"symbol": t, "holding": None})
        else:
            entries.append({"symbol": t["symbol"], "holding": t.get("holding")})
    return entries
