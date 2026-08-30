"""
fetcher.py — retrieves raw items from each source.

Returns a list of dicts:
  source_name : str
  title       : str
  url         : str
  summary     : str   (short excerpt, ~100-200 chars)
  body        : str   (capped at 2000 chars)
  author      : str   (empty if not available)
  image       : str   (URL of first image in content, empty if none)
  published   : str   (ISO 8601 or empty)
"""

import hashlib
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


def _extract_first_image(html: str) -> str:
    """Extract the first image URL from HTML content."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception:
        pass
    return ""


def _extract_author(entry: dict) -> str:
    """Extract author name from feedparser entry."""
    if hasattr(entry, "author"):
        return entry.author
    if hasattr(entry, "author_detail") and entry.author_detail:
        return entry.author_detail.get("name", "")
    if hasattr(entry, "authors") and entry.authors:
        return entry.authors[0].get("name", "") if entry.authors[0] else ""
    return ""


# ── Source-type handlers ───────────────────────────────────────────────────────

def fetch_rss(source: dict) -> list[dict]:
    items = []
    feed = feedparser.parse(source["url"])
    # Per-source cap: noisy feeds (hardware news at ~170 items) declare their
    # own `limit` so one source cannot dominate a run's API spend.
    for entry in feed.entries[:source.get("limit", 20)]:
        # Extract body (full HTML content or summary)
        body_html = ""
        if hasattr(entry, "content"):
            body_html = entry.content[0].value
        elif hasattr(entry, "summary"):
            body_html = entry.summary
        
        # Extract plain text body
        body = BeautifulSoup(body_html, "html.parser").get_text(separator=" ", strip=True)
        
        # Extract summary (short excerpt)
        summary = ""
        if hasattr(entry, "summary"):
            summary = BeautifulSoup(entry.summary, "html.parser").get_text(strip=True)
        
        # Extract author
        author = _extract_author(entry)
        
        # Extract first image
        image = _extract_first_image(body_html)
        
        items.append({
            "source_name": source["name"],
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "summary": summary,
            "body": body[:2000],
            "author": author,
            "image": image,
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
            
            # Reddit doesn't have author in JSON easily, skip for now
            # Extract image if available
            image = ""
            if p.get("url_overridden_by_dest"):
                url = p.get("url_overridden_by_dest", "")
                if url.lower().endswith((".jpg", ".png", ".gif", ".jpeg")):
                    image = url
            
            items.append({
                "source_name": source["name"],
                "title": p.get("title", ""),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "summary": "",
                "body": body[:2000],
                "author": p.get("author", ""),
                "image": image,
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
                "summary": "",
                "body": hit.get("story_text") or "",
                "author": hit.get("author", ""),
                "image": "",
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
                "summary": "",
                "body": body,
                "author": "",
                "image": "",
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
                "summary": "",
                "body": body,
                "author": "",
                "image": "",
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
                "summary": "",
                "body": body,
                "author": "",
                "image": "",
                "published": "",
            })
    except Exception as e:
        print(f"  [changelog error]: {e}")
    return items



# ── Hugging Face: the org watcher ─────────────────────────────────────────────
#
# ⭐ This is the source type the whole revival turns on. GitHub is the WRONG
# place to watch models: measured 2026-08-30, Wan2.2's last commit was March,
# Hunyuan3D-2's October, and Wan/Hunyuan3D/ACE-Step/TRELLIS/ComfyUI-GGUF cut no
# GitHub releases AT ALL. These orgs ship to Hugging Face and let the repo rot.
#
# The keyless HF API returns, in one call, the three things that decide whether
# a model is usable to us: its LICENCE, whether it is GATED, and its parameter
# count by dtype — from which we compute an approximate size, i.e. whether it
# clears brownie's hard 16GB wall.

_BYTES_PER_DTYPE = {
    "F64": 8, "I64": 8,
    "F32": 4, "I32": 4, "U32": 4,
    "BF16": 2, "F16": 2, "I16": 2, "U16": 2,
    "F8_E4M3": 1, "F8_E5M2": 1, "I8": 1, "U8": 1, "BOOL": 1,
    "F4": 0.5, "I4": 0.5, "U4": 0.5,
}


# A q4_K_M quantisation runs about 4.5 bits per parameter. Sanity check against
# our own machine: bosun-brain is a 27.8B model whose bf16 is 55.6GB and whose
# q4_K_M is 17.4GB on disk — this arithmetic gives ~14.6GB, close enough to be
# useful and deliberately labelled "roughly".
_Q4_BYTES_PER_PARAM = 4.5 / 8


def _hf_size_gb(safetensors: dict | None) -> tuple[float, str, float]:
    """
    Approximate published size in GB from the dtype breakdown, a human string,
    and the size a q4 quantisation would be. Returns zeros when HF reports no
    weights (common for GGUF-only repos, where there is nothing to measure).

    The q4 figure comes from the PARAMETER COUNT, not from scaling the
    published size — otherwise the same model would produce two different
    answers depending on whether the repo happens to be the bf16 or the fp8
    upload.
    """
    if not safetensors:
        return 0.0, "", 0.0
    params = safetensors.get("parameters") or {}
    if not params:
        return 0.0, "", 0.0
    total_bytes = 0.0
    for dtype, count in params.items():
        total_bytes += float(count) * _BYTES_PER_DTYPE.get(dtype, 2)
    gb = total_bytes / (1024 ** 3)
    n = safetensors.get("total") or sum(params.values())
    q4_gb = (n * _Q4_BYTES_PER_PARAM) / (1024 ** 3)
    return gb, f"~{gb:.1f}GB ({n/1e9:.1f}B params, {'/'.join(sorted(params))})", q4_gb


def _hf_license(tags: list[str]) -> str:
    for t in tags or []:
        if t.startswith("license:"):
            return t.split(":", 1)[1]
    return "unstated"


def fetch_hf_org(source: dict) -> list[dict]:
    """
    New models published by one Hugging Face org, newest first.

    `url` holds the org name (HF author matching is CASE-SENSITIVE — `ace-step`
    returns nothing, `ACE-Step` is the real org).
    """
    org = source["url"]
    limit = source.get("limit", 8)
    api = (
        "https://huggingface.co/api/models"
        f"?author={org}&sort=createdAt&direction=-1&limit={limit}"
        "&expand[]=createdAt&expand[]=downloads&expand[]=likes&expand[]=gated"
        "&expand[]=tags&expand[]=pipeline_tag&expand[]=safetensors"
    )
    resp = _get(api, timeout=25)
    if not resp:
        return []

    items = []
    try:
        models = resp.json()
        if not isinstance(models, list):
            print(f"  [hf error] {org}: {str(models)[:120]}")
            return []
        if not models:
            # An org that returns nothing is a NAME error, not a quiet week —
            # say so, because a silent zero is how a dead source hides.
            print(f"  [hf warning] org '{org}' returned 0 models — check the name (case-sensitive)")
            return []

        for m in models:
            mid = m.get("id", "")
            if not mid:
                continue
            lic = _hf_license(m.get("tags", []))
            gated = m.get("gated")
            gated_str = "NO" if gated in (False, None) else str(gated)
            size_gb, size_str, q4 = _hf_size_gb(m.get("safetensors"))
            # ⚠️ Say WHERE it could run, not just that it misses one ceiling.
            # An earlier version reported "EXCEEDS brownie's 16GB" for a 28GB
            # text model destined for the studio's 128GB — technically true and
            # so misleading that the filter skipped a genuine drop-in
            # replacement for our own brain. Two machines, two answers.
            #
            # The q4 figure matters as much as the raw one: our bosun-brain is
            # a 27B whose bf16 is 55.6GB and whose q4_K_M is 17.4GB — so a big
            # bf16 number is not a verdict, it is an input to one.
            fits = ""
            if size_gb:
                where = (
                    "fits brownie's 16GB VRAM" if size_gb <= 15.0
                    else "too big for brownie's 16GB, but fits the studio (~96GB usable)"
                    if size_gb <= 90.0
                    else "too big for either machine as published"
                )
                fits = f"{where}; a q4 quantisation would be roughly {q4:.0f}GB"

            body = (
                f"Hugging Face model {mid}.\n"
                f"Licence: {lic}. Gated: {gated_str}.\n"
                f"Size: {size_str or 'not reported by the API (often a GGUF-only repo)'}"
                + (f" — {fits}." if fits else ".") + "\n"
                f"Task: {m.get('pipeline_tag') or 'unstated'}. "
                f"Downloads: {m.get('downloads', 0)}. Likes: {m.get('likes', 0)}."
            )

            items.append({
                "source_name": source["name"],
                "title": f"New on Hugging Face: {mid}",
                "url": f"https://huggingface.co/{mid}",
                "summary": "",
                "body": body,
                "author": org,
                "image": "",
                "published": m.get("createdAt", "") or "",
            })
    except Exception as e:
        print(f"  [hf error] {org}: {e}")
    return items


# ── Page digest: watch a page that has no feed ────────────────────────────────

def fetch_page_digest(source: dict) -> list[dict]:
    """
    For a page with no feed whose VALUE IS ITS CHANGES — the model-deprecation
    tables. Emits one item whose URL carries a hash of the page's own content,
    so an unchanged page dedupes to nothing (free) and a changed page produces
    exactly one new item to judge.
    """
    resp = _get(source["url"], timeout=25)
    if not resp:
        return []
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "svg"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        text = re.sub(r"\s+", " ", main.get_text(separator=" ", strip=True)).strip()
        if not text:
            return []
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        return [{
            "source_name": source["name"],
            "title": f"{source['name']} — page changed",
            "url": f"{source['url']}#digest-{digest}",
            "summary": "",
            "body": text[:2000],
            "author": "",
            "image": "",
            "published": "",
        }]
    except Exception as e:
        print(f"  [page digest error] {source['url']}: {e}")
        return []


# ── Dispatch table ────────────────────────────────────────────────────────────

FETCH_FN = {
    "rss": fetch_rss,
    "reddit": fetch_reddit,
    "hn": fetch_hn,
    "scrape": fetch_scrape,
    "release_notes": fetch_release_notes,
    "changelog_md": fetch_changelog_md,
    "hf_org": fetch_hf_org,
    "page_digest": fetch_page_digest,
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
