"""
state.py — tracks which item URLs have already been seen (pre-filter).

This prevents re-sending the same item through the Claude filter on every run,
which would waste API calls and could produce duplicate feed entries.

Stored as a simple JSON set on disk.
"""

import json
import os

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "seen.json")


def load(path: str = DEFAULT_PATH) -> set[str]:
    if not os.path.exists(path):
        return set()
    try:
        with open(path) as f:
            return set(json.load(f))
    except Exception:
        return set()


def save(seen: set[str], path: str = DEFAULT_PATH):
    # Keep only the last 5000 URLs to prevent unbounded growth
    seen_list = list(seen)[-5000:]
    with open(path, "w") as f:
        json.dump(seen_list, f)


def filter_new(items: list[dict], seen: set[str]) -> list[dict]:
    """Return only items whose URL hasn't been seen before."""
    new = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            new.append(item)
    return new


def mark_seen(items: list[dict], seen: set[str]):
    """Add item URLs to the seen set (mutates in place)."""
    for item in items:
        url = item.get("url", "")
        if url:
            seen.add(url)
