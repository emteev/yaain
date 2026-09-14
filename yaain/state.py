"""
state.py — tracks which item URLs have already been seen (pre-filter).

This prevents re-sending the same item through the Claude filter on every run,
which would waste API calls and could produce duplicate feed entries.

Stored as a simple JSON list on disk, OLDEST FIRST.

⚠️ THE ORDER IS LOAD-BEARING, and it was not before 2026-09-14. `save()` did
`list(seen)[-CAP:]` on a Python set, whose iteration order is arbitrary — so
once the file passed the cap, the URLs it forgot were an arbitrary sample
rather than the oldest ones. A forgotten URL is re-fetched, re-judged and
re-published, which is precisely the "an old item arrives as news" failure the
age floor exists to stop; the two would have fought each other. At 2,021 URLs
the bug had not bitten yet, which is the only reason it was still there to
find. Keeping insertion order makes eviction mean what it says.
"""

import json
import os

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "seen.json")

# Keep the most recent N URLs. Sized against real volume: ~2,000 after two
# weeks of six-times-daily runs, so this is months of headroom.
CAP = 5000


class OrderedSeen:
    """A set that remembers what it learned first.

    Supports exactly what the pipeline uses — `in`, `.add()`, `len()`,
    iteration — so callers are unchanged, but iteration is insertion order,
    which is what makes "keep the newest CAP" a truthful statement.
    """

    __slots__ = ("_d",)

    def __init__(self, urls=()):
        self._d = dict.fromkeys(urls)

    def __contains__(self, url):
        return url in self._d

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def add(self, url):
        self._d[url] = None

    def as_list(self):
        return list(self._d)


def load(path: str = DEFAULT_PATH) -> OrderedSeen:
    if not os.path.exists(path):
        return OrderedSeen()
    try:
        with open(path) as f:
            return OrderedSeen(json.load(f))
    except Exception:
        return OrderedSeen()


def save(seen: OrderedSeen, path: str = DEFAULT_PATH):
    """Write the seen set, keeping the most recently added CAP urls."""
    urls = seen.as_list() if isinstance(seen, OrderedSeen) else list(seen)
    with open(path, "w") as f:
        json.dump(urls[-CAP:], f)


def filter_new(items: list[dict], seen) -> list[dict]:
    """Return only items whose URL hasn't been seen before."""
    new = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            new.append(item)
    return new


def mark_seen(items: list[dict], seen):
    """Add item URLs to the seen set (mutates in place)."""
    for item in items:
        url = item.get("url", "")
        if url:
            seen.add(url)
