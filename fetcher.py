"""
fetcher.py — retrieves raw items from each source.

Returns a list of dicts:
  source_name : str
  title       : str
  url         : str
  body        : str   (capped at 2000 chars)
  published   : str   (ISO 8601 or empty)
"""

import re
import time
import httpx
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse

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
        body = BeautifulSoup(body, "html.parser").get_text(separator=" ", strip=True)
        items.append({
            "source_name": source["name"],
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "body": body[:2000],
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
                continue
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
    cutoff = int(datetime.now(timezone.utc).timestamp()) - 86400
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
    """Generic link scraper — for Anthropic news/research index pages."""
    resp = _get(source["url"])
    if not resp:
        return []
    items = []
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        candidates = soup.select("article a, .post a, h2 a, h3 a, li a")
        if not candidates:
            candidates = soup.find_all("a", href=True)

        seen_urls = set()
        base_parsed = urlparse(source["url"])

        for a in candidates[:30]:
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue
            if href.startswith("/"):
                href = f"{base_parsed.scheme}://{base_parsed.netloc}{href}"
            if href in seen_urls:
                continue
            seen_urls.add(href)

            h = a.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            title = (h or a).get_text(separator=" ", strip=True)
            if len(title) > 140:
                title = title[:140].rsplit(" ", 1)[0] + "…"
            if len(title) < 10:
                continue

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


def fetch_release_notes(source: dict) -> list[dict]:
    """
    Parses the Anthropic release notes page (support.claude.com).
    The page is a single article: h3 = date, followed by paragraphs/lists.
    Each date block becomes one item.
    """
    resp = _get(source["url"])
    if not resp:
        return []
    items = []
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        # Each date heading is wrapped in div.intercom-interblocks-subheading3;
        # content lives in the sibling divs that follow it.
        date_containers = soup.find_all("div", class_="intercom-interblocks-subheading3")

        for container in date_containers[:14]:  # last ~2 weeks
            date_str = container.get_text(strip=True)
            if not date_str:
                continue

            chunks = []
            for sib in container.next_siblings:
                if hasattr(sib, "get") and "intercom-interblocks-subheading3" in sib.get("class", []):
                    break
                text = sib.get_text(separator=" ", strip=True) if hasattr(sib, "get_text") else ""
                if text:
                    chunks.append(text)

            body = " ".join(chunks)[:2000]
            if not body:
                continue

            # Stable URL: page URL + date as fragment (no external link per entry)
            slug = date_str.lower().replace(" ", "-").replace(",", "")
            url = f"{source['url']}#{slug}"

            items.append({
                "source_name": source["name"],
                "title": f"Release notes: {date_str}",
                "url": url,
                "body": body,
                "published": "",
            })
    except Exception as e:
        print(f"  [release notes error]: {e}")
    return items


def fetch_changelog_md(source: dict) -> list[dict]:
    """
    Parses a raw markdown changelog (e.g. Claude Code CHANGELOG.md).
    Each ## Version block becomes one item.
    """
    resp = _get(source["url"])
    if not resp:
        return []
    items = []
    try:
        # Split on ## version headings
        blocks = re.split(r'\n(?=## )', resp.text.strip())
        for block in blocks[:12]:  # most recent ~12 versions
            lines = block.strip().splitlines()
            if not lines:
                continue
            heading = lines[0].lstrip("# ").strip()
            if not heading:
                continue
            body = "\n".join(lines[1:]).strip()[:2000]
            if not body:
                continue

            # Stable URL: raw URL + heading as fragment
            slug = heading.lower().replace(" ", "-").replace(".", "")
            url = f"{source['url']}#{slug}"

            items.append({
                "source_name": source["name"],
                "title": f"Claude Code {heading}",
                "url": url,
                "body": body,
                "published": "",
            })
    except Exception as e:
        print(f"  [changelog error]: {e}")
    return items


# ── Dispatch table ────────────────────────────────────────────────────────────

FETCH_FN = {
    "rss": fetch_rss,
    "reddit": fetch_reddit,
    "hn": fetch_hn,
    "scrape": fetch_scrape,
    "release_notes": fetch_release_notes,
    "changelog_md": fetch_changelog_md,
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
        for item in items:
            item["_source_notes"] = source.get("notes", "")
        all_items.extend(items)
        time.sleep(0.5)
    return all_items
