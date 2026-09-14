"""
repair_feed.py — a ONE-TIME repair, kept because it documents what it did.

    python3.12 yaain/repair_feed.py --dry-run
    python3.12 yaain/repair_feed.py --apply

Two faults, both from the 2026-08-30 rebuild, both found on 2026-09-14:

  1. THE BACKFILL. A newly-added source's whole back catalogue is unseen on its
     first poll, so all of it was judged and published as news. 82% of the
     datable `act` tier predated the rebuild, some by seventeen months. The age
     floor in freshness.py stops this happening again; it cannot remove what is
     already in the feed. This does.

  2. THE DATES ARE WRONG. Until commit dd1c098 every rebuild re-dated every
     item to now, so the feed says 216 items were published on 2026-09-11.
     dd1c098 stopped the bleeding but repaired nothing, so the page a human
     reads still shows one date for nearly everything.

Both are fixed from the SOURCE's own record — the HF API's `createdAt`, the
GitHub release's `published_at`, the commit's committer date — never from the
feed's own pubDate, which is the thing that is untrustworthy.

⚠️ IT RE-DATES. IT DOES NOT DELETE, and that was a deliberate reversal.
The first version of this script dropped everything published before the
cutoff — 25 items. Reading the list before running it is what stopped it:
among the 25 were `LTX-2.3-22b-LoRA-Foley-Video` and the LTX-2.3 IC-LoRAs,
which are LoRAs for a model we actually run, and which stack.json's own
`revisit_if` calls "likely better value than the version bump". A blunt age
cut would have thrown away the most useful thing in the backfill.

The fault was never that those items exist. It was that a repo from April 2025
looked exactly like something published this morning. A truthful date fixes
that completely and loses nothing; deleting fixes it by destroying evidence and
requires an editorial call on 25 items nobody has made. So: every item keeps
its place, and gets its real date. The homepage then separates recent `act`
items from old unactioned ones, which is presentation, not judgement.

Rule, matching freshness.py: an item whose true date cannot be established is
left exactly as it is. Fail open.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freshness

HERE = os.path.dirname(os.path.abspath(__file__))
FEED = os.path.join(HERE, "..", "feed.xml")

# The backfill landed on this date; an item is judged against how old it was
# THEN, which is the moment the mistake was made.
REBUILD = datetime(2026, 8, 30, tzinfo=timezone.utc)
_cache = {}


def _get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "yaain-repair"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r)
    except Exception:
        return None


def true_date(link: str):
    """The item's date according to its own source, or None."""
    if not link:
        return None
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/releases/tag/(.+)$", link)
    if m:
        repo, tag = m.group(1), m.group(2)
        key = ("rel", repo)
        if key not in _cache:
            data = _get(f"https://api.github.com/repos/{repo}/releases?per_page=100") or []
            if isinstance(data, list):
                _cache[key] = {x.get("tag_name"): x.get("published_at") for x in data}
            else:
                _cache[key] = {}
            time.sleep(0.3)
        hit = _cache[key].get(tag)
        if hit:
            return hit
        # ⚠️ The listing is the newest 100 releases. llama.cpp cuts several a
        # DAY, so a tag from last week is already off the end of it — which is
        # how seven llama.cpp items kept their wrong date through the first
        # repair pass. Ask for the tag directly before giving up.
        one = _get(f"https://api.github.com/repos/{repo}/releases/tags/{tag}")
        time.sleep(0.3)
        return (one or {}).get("published_at")
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/commit/([0-9a-f]+)", link)
    if m:
        d = _get(f"https://api.github.com/repos/{m.group(1)}/commits/{m.group(2)}")
        time.sleep(0.3)
        return (((d or {}).get("commit") or {}).get("committer") or {}).get("date")
    if "huggingface.co/" in link:
        mid = link.split("huggingface.co/")[-1].strip("/")
        d = _get(f"https://huggingface.co/api/models/{mid}")
        time.sleep(0.2)
        return (d or {}).get("createdAt") or (d or {}).get("lastModified")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--drop-old", action="store_true",
                    help="ALSO delete items published before the cutoff. Off by "
                         "default and it should stay off — see the module docstring.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--feed", default=FEED)
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        ap.error("pass --dry-run or --apply")

    tree = ET.parse(args.feed)
    channel = tree.getroot().find("channel")
    items = channel.findall("item")
    print(f"{len(items)} items in the feed")

    cutoff = REBUILD - timedelta(days=freshness.MAX_AGE_DAYS)
    print(f"Anything published before {cutoff.date()} was already "
          f"{freshness.MAX_AGE_DAYS}+ days old at the 2026-08-30 rebuild.\n")

    old, redate, unknown = [], [], 0
    for it in items:
        link = it.findtext("link") or ""
        td = true_date(link)
        if not td:
            unknown += 1
            continue
        dt = freshness.parse_date(td)
        if dt is None:
            unknown += 1
            continue
        stamp = dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        if (it.findtext("pubDate") or "") != stamp:
            redate.append((it, stamp))
        if dt < cutoff:
            old.append((it, dt, it.findtext("title") or ""))

    print(f"  redate  {len(redate):>3}  the feed's date is wrong and can be fixed")
    print(f"  leave   {unknown:>3}  no establishable source date — fail open")
    print(f"  of which {len(old):>3} predate the cutoff: backfill, kept but now visibly old\n")

    for _, dt, title in sorted(old, key=lambda x: x[1]):
        print(f"    old  {dt.date()}  {title[:62]}")

    if args.dry_run:
        print("\nDry run. Nothing written.")
        return

    if args.drop_old:
        for it, _, _ in old:
            channel.remove(it)
    for it, stamp in redate:
        it.find("pubDate").text = stamp
    tree.write(args.feed, encoding="utf-8", xml_declaration=True)
    print(f"\nWritten: {len(redate)} re-dated, "
          f"{len(old) if args.drop_old else 0} removed, "
          f"{len(channel.findall('item'))} items remain.")


if __name__ == "__main__":
    main()
