"""
test_freshness.py — the age floor, and proof each check can fail.

    python3.12 yaain/test_freshness.py

Run it after any change to freshness.py or to state.py's eviction. Every
assertion here was watched to fail before it was allowed to pass.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import freshness
import state

NOW = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + ("" if ok else f"   got {got!r}, want {want!r}"))
    if not ok:
        fails.append(name)


def item(url, published):
    return {"url": url, "published": published, "title": url}


print("── parse_date: the shapes our fetchers actually emit ──")
check("ISO with Z (HF/GitHub API)", freshness.parse_date("2026-09-01T10:00:00Z").year, 2026)
check("ISO with offset", freshness.parse_date("2026-09-01T10:00:00+00:00").day, 1)
check("ISO naive is taken as UTC", freshness.parse_date("2026-09-01T10:00:00").tzinfo, timezone.utc)
check("RFC 822 (RSS)", freshness.parse_date("Mon, 01 Sep 2026 10:00:00 +0000").month, 9)
check("empty string -> None", freshness.parse_date(""), None)
check("None -> None", freshness.parse_date(None), None)
check("garbage -> None", freshness.parse_date("last Tuesday-ish"), None)
check("non-string -> None", freshness.parse_date(12345), None)

print("\n── split_by_age: the floor itself ──")
fresh, stale = freshness.split_by_age([
    item("today",      "2026-09-14T00:00:00Z"),
    item("44d",        (NOW - timedelta(days=44)).isoformat()),
    item("46d",        (NOW - timedelta(days=46)).isoformat()),
    item("17 months",  "2025-04-17T00:00:00Z"),
    item("no date",    ""),
    item("bad date",   "whenever"),
    item("future",     "2026-10-01T00:00:00Z"),
], now=NOW)
fresh_urls = {i["url"] for i in fresh}
stale_urls = {i["url"] for i in stale}
check("today is judged",              "today" in fresh_urls, True)
check("44 days is judged (inside 45)", "44d" in fresh_urls, True)
check("46 days is dropped",           "46d" in stale_urls, True)
check("the 17-month backfill is dropped", "17 months" in stale_urls, True)
check("undated FAILS OPEN — judged",  "no date" in fresh_urls, True)
check("unparseable FAILS OPEN — judged", "bad date" in fresh_urls, True)
check("future-dated is judged, not dropped", "future" in fresh_urls, True)
check("nothing is lost in the split", len(fresh) + len(stale), 7)

print("\n── the real backfill: would the floor have stopped it? ──")
# The genuine 2026-08-30 first-poll dates, from each source's own API.
REBUILD = datetime(2026, 8, 30, tzinfo=timezone.utc)
backfill = [
    item("city96/Wan2.1-FLF2V-gguf",  "2025-04-17T00:00:00Z"),
    item("city96/Qwen-Image-gguf",    "2025-08-05T00:00:00Z"),
    item("Wan2.2-Animate-14B",        "2025-09-11T00:00:00Z"),
    item("ComfyUI-GGUF Gemma3",       "2026-01-12T00:00:00Z"),
]
must_keep = [
    item("LTX-2.5",                   "2026-07-23T00:00:00Z"),  # the acceptance case
    item("Qwen3.8-27B",               "2026-08-05T00:00:00Z"),
    item("trellis.cpp v0.6.0",        "2026-08-19T00:00:00Z"),
]
f2, s2 = freshness.split_by_age(backfill + must_keep, now=REBUILD)
check("all 4 backfill items dropped at first poll", len(s2), 4)
check("LTX-2.5 SURVIVES the floor", "LTX-2.5" in {i["url"] for i in f2}, True)
check("nothing we wanted was dropped", len(f2), 3)

print("\n── state.save: eviction must drop the OLDEST, not an arbitrary set ──")
tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_seen.json")
try:
    state.CAP = getattr(state, "CAP", 5000)
    seen = state.load(tmp)  # missing file
    check("missing state file loads empty", len(seen), 0)
    # Fill past the cap in a known order, then confirm the survivors are the newest.
    cap = state.CAP
    first = [f"u{i}" for i in range(cap + 100)]
    state.mark_seen([{"url": u} for u in first], seen)
    state.save(seen, tmp)
    kept = json.load(open(tmp))
    check("saved file is capped", len(kept), cap)
    check("the OLDEST were evicted", "u0" in kept, False)
    check("the NEWEST were kept", f"u{cap + 99}" in kept, True)
    # A reload must still suppress a recent item, which is the whole point.
    reloaded = state.load(tmp)
    check("a recent url is still remembered after reload", f"u{cap + 50}" in reloaded, True)
finally:
    if os.path.exists(tmp):
        os.remove(tmp)

print()
if fails:
    print(f"FAILED — {len(fails)}: {', '.join(fails)}")
    sys.exit(1)
print(f"All checks passed.")
