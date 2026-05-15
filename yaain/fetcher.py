"""
fetcher.py — retrieves raw items from each source.

Returns a list of dicts:
  source_name : str
  title       : str
  url         : str
  body        : str   (as much text as we can get)
  published   : str   (ISO 8601 or empty)
"""

import time
import httpx
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "YAAIN-feed-bot/1.0 (claude-newsletter; contact: emteev2026@gmail.com)"
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 15) -> httpx.Response | None:
    try:
        r = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return None


def _iso(t) -> str:
    """Convert feedparser time struct or string to ISO 8601."""
    if not t:
        return ""
    if isinstance(t, time.struct_time):
        return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return str(t)


# ── Source-type handlers ───────────────────────────────────────────────────────

def fetch_rss(source: dict) -> list[dict]:
    items = []
    feed = feedparser.parse(source["url"])
    for entry in feed.entries[:20]:
        body = ""
        if hasattr(entry, "content"):
            body = entry.content[0].value
        elif hasattr(entry, "summary"):
            body = entry.summary
        # Strip HTML tags for clean text
        body = BeautifulSoup(body, "html.parser").get_text(separator=" ", strip=True)
        items.append({
            "source_name": source["name"],
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "body": body[:2000],  # cap to keep token cost reasonable
            "published": _iso(entry.get("published_parsed") or entry.get("updated_parsed")),
        })
    return items


def fetch_reddit(source: dict) -> list[dict]:
    resp = _get(source["url"])
    if not resp:
        return []
    items = []
    try:
        data = resp.json()
        for post in data["data"]["children"]:
            p = post["data"]
            if p.get("score", 0) < 10:
                continue  # skip very low-signal posts
            body = p.get("selftext", "").strip()
            if body in ("[removed]", "[deleted]"):
                body = ""
            items.append({
                "source_name": source["name"],
                "title": p.get("title", ""),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "body": body[:2000],
                "published": datetime.fromtimestamp(
                    p.get("created_utc", 0), tz=timezone.utc
                ).isoformat(),
            })
    except Exception as e:
        print(f"  [reddit parse error] {source['name']}: {e}")
    return items


def fetch_hn(source: dict) -> list[dict]:
    cutoff = int((datetime.now(timezone.utc).timestamp()) - 86400)  # last 24h
    url = source["url"].format(cutoff)
    resp = _get(url)
    if not resp:
        return []
    items = []
    try:
        data = resp.json()
        for hit in data.get("hits", []):
            if hit.get("points", 0) < 20:
                continue
            items.append({
                "source_name": source["name"],
                "title": hit.get("title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "body": hit.get("story_text") or "",
                "published": hit.get("created_at", ""),
            })
    except Exception as e:
        print(f"  [hn parse error]: {e}")
    return items


def fetch_scrape(source: dict) -> list[dict]:
    """
    Generic scraper for Anthropic pages.
    Extracts <a> links + surrounding text from the page.
    Each distinct linked item becomes a candidate.
    """
    resp = _get(source["url"])
    if not resp:
        return []
    items = []
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        # Look for article-like elements first, fall back to all links
        candidates = soup.select("article a, .post a, h2 a, h3 a, li a")
        if not candidates:
            candidates = soup.find_all("a", href=True)

        seen_urls = set()
        for a in candidates[:30]:
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue
            # Make absolute
            if href.startswith("/"):
                from urllib.parse import urlparse
                base = source["url"]
                parsed = urlparse(base)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Prefer a heading element inside the link for a clean title.
            h = a.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if h and h.get_text(strip=True):
                title = h.get_text(strip=True)
            else:
                # Use space separator so concatenated chunks don't smash together.
                title = a.get_text(separator=" ", strip=True)
                if len(title) > 140:
                    title = title[:140].rsplit(" ", 1)[0] + "…"
            if len(title) < 10:
                continue  # skip nav/icon links

            # Grab surrounding paragraph text as body
            parent = a.find_parent(["li", "p", "article", "div"])
            body = parent.get_text(separator=" ", strip=True)[:500] if parent else ""

            items.append({
                "source_name": source["name"],
                "title": title,
                "url": href,
                "body": body,
                "published": "",
            })
    except Exception as e:
        print(f"  [scrape error] {source['name']}: {e}")
    return items


# ── Main entry ────────────────────────────────────────────────────────────────

FETCH_FN = {
    "rss": fetch_rss,
    "reddit": fetch_reddit,
    "hn": fetch_hn,
    "scrape": fetch_scrape,
}


def fetch_all(sources: list[dict]) -> list[dict]:
    all_items = []
    for source in sources:
        fn = FETCH_FN.get(source["type"])
        if not fn:
            print(f"  [unknown type] {source['type']}")
            continue
        print(f"  Fetching {source['name']}...")
        items = fn(source)
        # Attach source notes for the filter prompt
        for item in items:
            item["_source_notes"] = source.get("notes", "")
        all_items.extend(items)
        time.sleep(0.5)  # be polite
    return all_items
