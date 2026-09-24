"""Recent news headlines plus a simple keyword-based sentiment score.

This is NOT real NLP sentiment analysis - it's a transparent word-count
heuristic (count positive finance words minus negative ones per headline).
Treat it as a rough signal, not a fact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

_POSITIVE_WORDS = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "rallies",
    "upgrade", "upgraded", "growth", "record", "profit", "profits", "gain",
    "gains", "strong", "outperform", "bullish", "buy", "raises", "raised",
    "expansion", "win", "wins", "positive", "boost", "boosts", "recovery",
}

_NEGATIVE_WORDS = {
    "miss", "misses", "plunge", "plunges", "slump", "slumps", "fall", "falls",
    "downgrade", "downgraded", "loss", "losses", "decline", "declines",
    "weak", "underperform", "bearish", "sell", "cuts", "cut", "lawsuit",
    "investigation", "recall", "layoffs", "bankruptcy", "warning", "negative",
    "slowdown", "fraud", "probe",
}

_WORD_RE = re.compile(r"[a-zA-Z']+")


@dataclass
class NewsItem:
    title: str
    publisher: str
    published: Optional[datetime]
    link: str
    sentiment: int  # positive-word count minus negative-word count


def _score_headline(title: str) -> int:
    words = {w.lower() for w in _WORD_RE.findall(title)}
    return len(words & _POSITIVE_WORDS) - len(words & _NEGATIVE_WORDS)


def fetch_news(symbol: str, limit: int = 5) -> list[NewsItem]:
    """Best-effort fetch; returns [] on any failure rather than raising."""
    try:
        raw = yf.Ticker(symbol).news or []
    except Exception:
        return []

    items = []
    for entry in raw[:limit]:
        content = entry.get("content", entry)
        title = content.get("title") or entry.get("title") or ""
        if not title:
            continue
        publisher = (
            (content.get("provider") or {}).get("displayName")
            or entry.get("publisher")
            or "Unknown source"
        )
        link = (content.get("canonicalUrl") or {}).get("url") or entry.get("link") or ""
        pub_date = content.get("pubDate")
        published = None
        if pub_date:
            try:
                published = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            except ValueError:
                published = None
        elif entry.get("providerPublishTime"):
            published = datetime.fromtimestamp(entry["providerPublishTime"], tz=timezone.utc)

        items.append(
            NewsItem(
                title=title,
                publisher=publisher,
                published=published,
                link=link,
                sentiment=_score_headline(title),
            )
        )
    return items
