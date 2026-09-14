"""
freshness.py — an age floor, applied BEFORE anything is judged.

⚠️ WHY THIS EXISTS, measured not assumed (2026-09-14).

On 2026-09-14 the `act` tier held 89 items. Dating each one against its own
source API showed that **82% of the datable ones predated the 2026-08-30
rebuild** — some by seventeen months (city96 GGUFs published 2025-04-17,
Qwen-Image-gguf 2025-08-05). None of it was news. It was the FIRST POLL of a
newly-added source reading that source's whole back catalogue as unseen.

The mechanism is structural, not a bug in any one fetcher. `hf_org` asks for
the newest N repos by `createdAt`; for an org that publishes rarely, "newest 8"
reaches back years. A releases feed behaves the same way. Every one of those is
genuinely unseen on day one, so every one gets judged, and a model asked "is
this a new variant of something we run?" correctly answers yes — about a repo
published last spring.

So the fix is NOT a prompt change. Reaching for the prompt here would have been
the exact mistake this project has already made twice (repo-hunter projectfit
2026-08-21/22): tuning a classifier that was answering its question correctly,
against a fault that lived somewhere else entirely.

THE FLOOR IS 45 DAYS, and that number is measured rather than picked. Replaying
the real backfill:

    floor    would have dropped        keeping
     7d      47 of 64  (73%)           17
    14d      40 of 64  (62%)           24
    30d      30 of 64  (46%)           34   ← DROPS LTX-2.5
    45d      21 of 64  (32%)           43   ← keeps everything that mattered
    90d      16 of 64  (25%)           48

LTX-2.5 was published 2026-07-23, 38 days before the rebuild, and it is the
live case in acceptance.py — the one genuine miss the whole rebuild existed to
catch. A 30-day floor throws it away. 45 is the smallest round number that
keeps it, which also sets the tolerance in plain terms: **YAAIN can stop for six
weeks and still catch up without missing anything.** Longer than that and a
resumed source starts reporting history as news again.

TWO RULES, both deliberate:

  1. FAIL OPEN. An item with no date, or a date we cannot parse, is KEPT and
     judged. Several sources legitimately carry no date (the doc-changelog
     watchers hash a page rather than read a timestamp). A floor that silently
     ate undated items would be a filter nobody could see working.

  2. DROPPED IS STILL SEEN. A dropped item is marked in seen.json exactly as a
     judged one is, so it is never reconsidered. Without that it would be
     re-fetched and re-dropped on all six runs a day forever — cheap, but it
     would make the per-run counts lie about what the pipeline is doing.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Six weeks. See the module docstring — this is measured against the real
# 2026-08-30 backfill, not chosen for feel. Raising it re-admits history;
# lowering it past ~38 days starts dropping things we would want.
MAX_AGE_DAYS = 45


def parse_date(value: str):
    """Parse the date shapes our fetchers actually produce, else None.

    ISO 8601 from the HF and GitHub APIs; RFC 822 from RSS. Anything else is
    None, which the caller treats as 'keep' — see rule 1.
    """
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def age_days(value: str, now: datetime | None = None):
    """Age of a date string in days, or None if it has no usable date."""
    dt = parse_date(value)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 86400.0


def split_by_age(items: list[dict], max_age_days: int = MAX_AGE_DAYS,
                 now: datetime | None = None) -> tuple[list[dict], list[dict]]:
    """Split items into (fresh_enough_to_judge, too_old).

    Fresh-enough includes every item whose date is missing or unparseable.
    A future-dated item is fresh, not suspect: clock skew between a source and
    the runner is ordinary, and treating it as old would drop real news.
    """
    fresh, stale = [], []
    for item in items:
        age = age_days(item.get("published", ""), now=now)
        if age is not None and age > max_age_days:
            stale.append(item)
        else:
            fresh.append(item)
    return fresh, stale
