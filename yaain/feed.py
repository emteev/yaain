"""
feed.py — generates and updates a valid RSS 2.0 feed file.
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from xml.dom import minidom

FEED_TITLE = "YAAIN — Claude Signal"
FEED_DESCRIPTION = "High-signal Claude family content, filtered daily for professional practitioners."
FEED_LINK = "https://github.com/hotstacks/yaain"  # update to your actual URL
MAX_ITEMS = 100  # keep the last N items in the feed


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
            items.append({
                "guid": guid,
                "title": title,
                "url": link,
                "description": desc,
                "published": pubdate,
                "source_name": source_name,
            })
    except Exception as e:
        print(f"  [feed parse warning] {e} — starting fresh")
    return items


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
