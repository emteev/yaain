"""
main.py — YAAIN pipeline orchestrator.

Usage:
    ANTHROPIC_API_KEY=sk-... python main.py

Optional env vars:
    FEED_PATH   : path to write feed.xml (default: ../feed.xml)
    STATE_PATH  : path to seen.json (default: ./seen.json)
"""

import os
import sys

from sources import SOURCES
from fetcher import fetch_all
from filter import filter_items
from feed import load_existing_items, build_feed
import state as state_module


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    feed_path = os.environ.get(
        "FEED_PATH",
        os.path.join(os.path.dirname(__file__), "..", "feed.xml"),
    )
    state_path = os.environ.get(
        "STATE_PATH",
        os.path.join(os.path.dirname(__file__), "seen.json"),
    )

    print("── YAAIN ─────────────────────────────────────────")
    print("Step 1: Fetching sources...")
    candidates = fetch_all(SOURCES)
    print(f"  {len(candidates)} candidate items fetched")

    print("Step 2: Deduplicating against seen items...")
    seen = state_module.load(state_path)
    new_candidates = state_module.filter_new(candidates, seen)
    print(f"  {len(new_candidates)} new (unseen) items")

    if not new_candidates:
        print("  Nothing new to process. Done.")
        return

    print("Step 3: Filtering with Claude...")
    passed = filter_items(new_candidates, api_key)
    print(f"  {len(passed)} items passed the filter")

    print("Step 4: Updating feed...")
    existing = load_existing_items(feed_path)
    build_feed(passed, existing, feed_path)

    print("Step 5: Saving state...")
    state_module.mark_seen(new_candidates, seen)
    state_module.save(seen, state_path)

    print("── Done ──────────────────────────────────────────")


if __name__ == "__main__":
    main()
