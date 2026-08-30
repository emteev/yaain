"""
feed.py — generates and updates a valid RSS 2.0 feed file.
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from xml.dom import minidom

FEED_TITLE = "YAAIN — stack signal"
FEED_DESCRIPTION = (
    "AI news filtered against one specific stack: what changed that affects "
    "something we actually run. Tiered act / watch / context."
)
FEED_LINK = "https://emteev.github.io/yaain"
MAX_ITEMS = 250  # ~a week at current volume; the homepage renders from this


def _rfc822(iso_str: str) -> str:
    """Convert ISO 8601 to RFC 822 for RSS."""
    if not iso_str:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def _cdata(text: str) -> str:
    return f"<![CDATA[{text}]]>"


def load_existing_items(feed_path: str) -> list[dict]:
    """Parse existing feed.xml and return current items as dicts."""
    if not os.path.exists(feed_path):
        return []
    items = []
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
        channel = root.find("channel")
        if channel is None:
            return []
        for item_el in channel.findall("item"):
            guid = item_el.findtext("guid") or ""
            title = item_el.findtext("title") or ""
            link = item_el.findtext("link") or ""
            desc = item_el.findtext("description") or ""
            pubdate = item_el.findtext("pubDate") or ""
            source_name = item_el.findtext("source") or ""
            author = item_el.findtext("author") or ""
            image = item_el.findtext("image") or ""
            # Verdict + affected stack item ride as standard RSS <category>
            # elements, distinguished by their `domain` attribute, so the feed
            # stays valid RSS 2.0 and ordinary readers show them sensibly.
            verdict, affects = "", ""
            for cat in item_el.findall("category"):
                if cat.get("domain") == "verdict":
                    verdict = (cat.text or "").strip()
                elif cat.get("domain") == "stack":
                    affects = (cat.text or "").strip()
            items.append({
                "guid": guid,
                "title": title,
                "url": link,
                "description": desc,
                "published": pubdate,
                "source_name": source_name,
                "author": author,
                "image": image,
                "verdict": verdict,
                "affects": affects,
            })
    except Exception as e:
        print(f"  [feed parse warning] {e} — starting fresh")
    return items


def touch_feed(feed_path: str) -> bool:
    """
    Refresh only <lastBuildDate>, leaving every item untouched.

    ⚠️ This exists so feed.xml is a HEARTBEAT, not just an archive. Without it,
    "the pipeline ran and found nothing" and "the pipeline is dead" leave
    identical traces — a feed that stopped changing — and the watchdog cannot
    tell them apart. With it, a stale lastBuildDate means the run stopped
    happening, which is the thing worth an alarm.
    """
    if not os.path.exists(feed_path):
        return False
    try:
        tree = ET.parse(feed_path)
        channel = tree.getroot().find("channel")
        if channel is None:
            return False
        el = channel.find("lastBuildDate")
        if el is None:
            el = ET.SubElement(channel, "lastBuildDate")
        el.text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        tree.write(feed_path, encoding="utf-8", xml_declaration=True)
        return True
    except Exception as e:
        print(f"  [feed touch warning] {e}")
        return False


def build_feed(new_items: list[dict], existing_items: list[dict], feed_path: str, blocklist: set | None = None):
    """Merge new items into the feed, write to feed_path."""
    blocklist = blocklist or set()
    if blocklist:
        new_items = [it for it in new_items if it.get("url") not in blocklist]
        existing_items = [it for it in existing_items if it.get("guid") not in blocklist]
    existing_guids = {item["guid"] for item in existing_items}

    added = 0
    for item in new_items:
        guid = item.get("url", "")
        if guid in existing_guids:
            continue  # already in feed
        summary = item.get("summary", "")
        why = item.get("why", "")
        description = f"{summary}"
        if why:
            description += f" {why}"

        existing_items.insert(0, {
            "guid": guid,
            "title": item.get("title", ""),
            "url": guid,
            "description": description,
            "published": item.get("published", ""),
            "source_name": item.get("source_name", ""),
            "author": item.get("author", ""),
            "image": item.get("image", ""),
            "verdict": item.get("verdict", ""),
            "affects": item.get("affects", ""),
        })
        added += 1

    # Trim to max
    existing_items = existing_items[:MAX_ITEMS]

    # Build XML
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = FEED_TITLE
    ET.SubElement(channel, "link").text = FEED_LINK
    ET.SubElement(channel, "description").text = FEED_DESCRIPTION
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )
    atom_link = ET.SubElement(channel, "atom:link")
    atom_link.set("href", FEED_LINK + "/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for item in existing_items:
        item_el = ET.SubElement(channel, "item")
        ET.SubElement(item_el, "title").text = item["title"]
        ET.SubElement(item_el, "link").text = item["url"]
        ET.SubElement(item_el, "guid", isPermaLink="true").text = item["guid"]
        ET.SubElement(item_el, "pubDate").text = _rfc822(item["published"])
        ET.SubElement(item_el, "source").text = item["source_name"]
        # Author and image (optional, from source)
        if item.get("author"):
            ET.SubElement(item_el, "author").text = item["author"]
        if item.get("image"):
            ET.SubElement(item_el, "image").text = item["image"]
        if item.get("verdict"):
            ET.SubElement(item_el, "category", domain="verdict").text = item["verdict"]
        if item.get("affects"):
            ET.SubElement(item_el, "category", domain="stack").text = item["affects"]
        # Description as plain text (summaries are already clean)
        ET.SubElement(item_el, "description").text = item["description"]

    # Pretty-print
    raw = ET.tostring(rss, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding=None)
    # minidom adds an XML declaration; keep it
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(pretty)

    print(f"  Feed updated: {added} new item(s), {len(existing_items)} total → {feed_path}")
    return added
