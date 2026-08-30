"""
main.py — YAAIN pipeline orchestrator.

    ANTHROPIC_API_KEY=sk-... python yaain/main.py

Env:
    FEED_PATH      path to write feed.xml        (default: ../feed.xml)
    STATE_PATH     path to seen.json             (default: ./seen.json)
    BLOCKLIST_PATH path to blocklist.json        (default: ../blocklist.json)
    STACK_PATH     path to stack.json            (default: ./stack.json)
    YAAIN_DRY_RUN  '1' = fetch and dedupe only. No API calls, nothing written.
                   Use this to check source health and item volume for free.
"""

import json
import os
import sys
from collections import Counter

from sources import SOURCES
from fetcher import fetch_all
from filter import filter_items
from feed import load_existing_items, build_feed, touch_feed
import state as state_module
import stack as stack_module


def main():
    dry_run = os.environ.get("YAAIN_DRY_RUN") == "1"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not dry_run:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    here = os.path.dirname(__file__)
    feed_path = os.environ.get("FEED_PATH", os.path.join(here, "..", "feed.xml"))
    state_path = os.environ.get("STATE_PATH", os.path.join(here, "seen.json"))
    blocklist_path = os.environ.get("BLOCKLIST_PATH", os.path.join(here, "..", "blocklist.json"))
    stack_path = os.environ.get("STACK_PATH", os.path.join(here, "stack.json"))

    print("── YAAIN ─────────────────────────────────────────")
    if dry_run:
        print("DRY RUN — fetching only. No API calls, nothing written.")

    print(f"Step 0: Loading the stack manifest ({os.path.basename(stack_path)})...")
    stack = stack_module.load(stack_path)
    print(f"  {len(stack.get('models', []))} models, {len(stack.get('tools', []))} tools, "
          f"{len(stack.get('machines', []))} machines · updated {stack.get('updated', '?')}")

    print(f"Step 1: Fetching {len(SOURCES)} sources...")
    candidates = fetch_all(SOURCES)
    print(f"  {len(candidates)} candidate items fetched")

    # A source that returns nothing is not automatically broken (an empty
    # releases.atom is normal for a repo that cuts no releases) — but it should
    # be VISIBLE, because a silently dead source is how this project got into
    # trouble the first time.
    got = Counter(c.get("source_name", "?") for c in candidates)
    silent = [s["name"] for s in SOURCES if got.get(s["name"], 0) == 0]
    if silent:
        print(f"  ⚠️  {len(silent)} source(s) returned nothing: {', '.join(silent)}")

    print("Step 2: Deduplicating against seen items...")
    seen = state_module.load(state_path)
    new_candidates = state_module.filter_new(candidates, seen)
    print(f"  {len(new_candidates)} new (unseen) items")

    if dry_run:
        print("\n  Per-source yield (fetched / new):")
        newc = Counter(c.get("source_name", "?") for c in new_candidates)
        for s in SOURCES:
            n = s["name"]
            flag = "  ⚠️ SILENT" if got.get(n, 0) == 0 else ""
            print(f"    {got.get(n,0):>3} / {newc.get(n,0):>3}  {n}{flag}")
        print(f"\n  Would send {len(new_candidates)} items to the filter.")
        print("── Dry run done. Nothing spent, nothing written. ──")
        return

    if not new_candidates:
        # Still stamp the feed, so "ran and found nothing" is distinguishable
        # from "stopped running" — the watchdog reads lastBuildDate.
        if touch_feed(feed_path):
            print("  Nothing new to process. Feed heartbeat stamped. Done.")
        else:
            print("  Nothing new to process. Done.")
        return

    print("Step 3: Filtering against the stack...")
    passed = filter_items(new_candidates, api_key, stack)
    tiers = Counter(p.get("verdict", "?") for p in passed)
    print(f"  {len(passed)} of {len(new_candidates)} passed "
          f"(act {tiers.get('act',0)} · watch {tiers.get('watch',0)} · context {tiers.get('context',0)})")

    print("Step 4: Updating feed...")
    blocklist = set()
    if os.path.exists(blocklist_path):
        try:
            with open(blocklist_path) as f:
                blocklist = set(json.load(f))
            if blocklist:
                print(f"  Blocklist: {len(blocklist)} url(s) excluded")
        except Exception as e:
            print(f"  [blocklist warning] {e}")
    existing = load_existing_items(feed_path)
    build_feed(passed, existing, feed_path, blocklist)

    print("Step 5: Saving state...")
    # ⚠️ Mark ALL candidates seen, not just the ones that passed. A rejected
    # item must never be re-sent to the filter — otherwise every reject is
    # re-judged on all six runs a day, forever. (The never-executed root copy
    # of this file had `mark_seen(passed)`, which is that bug.)
    state_module.mark_seen(new_candidates, seen)
    state_module.save(seen, state_path)

    print("── Done ──────────────────────────────────────────")


if __name__ == "__main__":
    main()
