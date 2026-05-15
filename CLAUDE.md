# YAAIN — Technical Reference

**Project:** Yet Another AI Newsletter  
**Owner:** Hot Stacks (Em)  
**Purpose:** Daily pipeline that crawls defined sources, filters for Claude-family content using Claude Sonnet 4.6, writes a valid RSS 2.0 feed to `feed.xml`, and serves a tiered homepage of editorially ranked items via GitHub Pages.  
**Automation:** GitHub Actions runs `yaain/main.py` daily at noon UTC. On success it commits `feed.xml`, `yaain/seen.json`, `ratings.json`, and `blocklist.json` back to the repo. GitHub Pages serves the repo root.

---

## File Map

```
YAAIN/
  yaain/
    main.py         Orchestrator. Runs the full pipeline in sequence.
    sources.py      Source definitions. Edit this to add/remove/change sources.
    fetcher.py      Fetches raw items from each source by type.
    filter.py       Claude API filter. Returns include/summary/why per item.
    feed.py         Reads and writes feed.xml. Caps feed at 100 items.
    state.py        Reads and writes seen.json. Caps seen URLs at 5000.
    requirements.txt
    .env.example
    seen.json       Generated on first run. Do not edit manually.
  .github/
    workflows/
      daily.yml     GitHub Actions cron + manual-dispatch definition.
  feed.xml          Generated RSS feed. Do not edit manually.
  ratings.json      {url: 0–5} written by rank.html. Read by index.html.
  blocklist.json    [url, …] of permanently excluded items. Written by rank.html
                    when a slider goes to 5. Read by feed.py.
  index.html        Public homepage. Reads feed.xml + ratings.json + blocklist.json
                    from same origin. Renders tiered layout. Polls every 5 min.
  rank.html         Private feeder. Password-gated. Reads same files. Commits
                    ratings.json/blocklist.json via the GitHub Contents API.
```

GitHub Pages is enabled on the repo (Settings → Pages → Deploy from `main` / root). The site URL is `https://emteev.github.io/yaain/`.

---

## Data Flow

Two loops share the same repo as a state store.

### Loop A — Daily pipeline (writes feed.xml)

```
GitHub Actions (noon UTC, or manual workflow_dispatch)
  → yaain/main.py
    → fetch_all(SOURCES)              # fetcher.py — raw item dicts
    → filter_new(items, seen)         # state.py — drops URLs in seen.json
    → filter_items(new, api_key)      # filter.py — Claude API, drops non-Claude content
    → load blocklist.json             # main.py — set of URLs to permanently exclude
    → load_existing_items(feed_path)  # feed.py — parses current feed.xml
    → build_feed(passed, existing, feed_path, blocklist)
                                      # feed.py — merges, drops blocklisted, writes XML
    → mark_seen + save                # state.py — updates seen.json
  → Actions commits feed.xml, seen.json, ratings.json, blocklist.json
```

### Loop B — Rating loop (writes ratings.json + blocklist.json)

```
You → rank.html (gated by password + GitHub PAT)
  → fetches feed.xml + ratings.json + blocklist.json (via GitHub Pages)
  → renders items with 0–5 sliders, pre-filled from ratings.json
  → on slider change (1s debounce):
      ratings[url] = value
      if value == 5: add url to blocklist
      PUT ratings.json + blocklist.json via GitHub Contents API
  → GitHub commits land in repo → Pages serves new files within ~60s

Reader → index.html
  → fetches feed.xml + ratings.json + blocklist.json (cache-busted, every 5 min)
  → renders 1=hero, 2=2-col, 3=4-col, 4=bullet; hides 0 and 5
```

The next run of Loop A reads `blocklist.json` and drops any blocked URL from `feed.xml`, both new and existing.

---

## Function Contracts

### `fetcher.py`

**`fetch_all(sources: list[dict]) → list[dict]`**  
Iterates sources, dispatches to the correct handler by `source["type"]`, sleeps 0.5s between requests. Returns all raw items concatenated.

Each returned item contains:
- `source_name: str`
- `title: str`
- `url: str`
- `body: str` — capped at 2000 chars
- `published: str` — ISO 8601 or empty string
- `_source_notes: str` — source context passed to the filter prompt

**`fetch_rss(source) → list[dict]`**  
Parses RSS/Atom via feedparser. Takes up to 20 entries. Strips HTML from body.

**`fetch_reddit(source) → list[dict]`**  
Hits Reddit's JSON API directly (no auth). Skips posts with score < 10. Skips removed/deleted body text.

**`fetch_hn(source) → list[dict]`**  
Hits Algolia HN API filtered to last 24h. Skips stories with score < 20. Falls back to HN item URL if no external URL.

**`fetch_scrape(source) → list[dict]`**  
Generic scraper for Anthropic pages. For each link, prefers an inner heading element (`h1`–`h6`) for the title; falls back to space-separated text from the link, truncated at 140 chars. Skips links with text under 10 chars. Takes up to 30 distinct URLs per page.

---

### `filter.py`

**`filter_items(items: list[dict], api_key: str) → list[dict]`**  
Calls `claude-sonnet-4-6` once per item. System prompt instructs Claude to include only content specifically about the Claude family of products (claude.ai, API, Claude Code, Cowork, Anthropic research).

Returns only passing items. Each passing item has:
- `summary: str` — 2 sentences, factual, no filler
- `why: str` — 1 sentence, practitioner relevance
- `body` and `_source_notes` removed

Model response must be a JSON object: `{"include": bool, "summary": str, "why": str}`. Strips markdown code fences if present before parsing.

**Filter exclusions (hardcoded in system prompt):**
- General AI news not specific to Claude
- Other AI products unless directly compared to Claude usefully
- Opinion without concrete Claude-specific information
- Hype, vague announcements
- Beginner-level how-to content

---

### `feed.py`

**`load_existing_items(feed_path: str) → list[dict]`**  
Parses `feed.xml` if it exists. Returns list of item dicts with keys: `guid`, `title`, `url`, `description`, `published`, `source_name`. Returns empty list if file missing or unparseable.

**`build_feed(new_items, existing_items, feed_path, blocklist=None) → int`**  
Deduplicates new items against existing by URL (used as guid). If `blocklist` is provided, drops any URL it contains from both new and existing items before merging. Prepends remaining new items to the front of the list. Trims to 100 items. Writes pretty-printed RSS 2.0 XML to `feed_path`. Returns count of items added.

Item description field = `summary` + `why` concatenated as plain text.

---

### `state.py`

**`load(path) → set[str]`** — reads seen.json, returns set of URLs. Returns empty set if missing.  
**`save(seen, path)`** — writes last 5000 URLs to seen.json.  
**`filter_new(items, seen) → list[dict]`** — returns items whose URL is not in seen.  
**`mark_seen(items, seen)`** — adds item URLs to seen set in place.

State is saved after filtering (not after fetching), so only items that went through the Claude filter are marked seen. If the Claude API call fails for an item, that item will be retried on the next run.

---

### `sources.py`

Each source is a dict:
```python
{
    "name": str,   # display name, used in feed and logs
    "type": str,   # "rss" | "reddit" | "hn" | "scrape"
    "url": str,    # endpoint
    "notes": str,  # context injected into the Claude filter prompt
}
```

To add a source: append a dict to the `SOURCES` list. To remove: delete or comment out its entry. To change the filter behavior for a source: edit its `notes` field — this text is passed directly to Claude.

---

### `index.html`

Public homepage served from GitHub Pages.

- Fetches `feed.xml`, `ratings.json`, `blocklist.json` from the same origin with cache-busting query strings.
- Polls every 5 minutes.
- For each `<item>` in feed.xml, looks up the rating by URL. Drops items with rating 0 or 5 or in the blocklist.
- Renders by tier:
  - **1** — hero. Full-width headline, summary + why as paragraphs, byline.
  - **2** — 2-column band. Headline + summary paragraph.
  - **3** — 4-column band. Headline + truncated summary.
  - **4** — bulleted line. Headline · source · date.
- Source name drives a per-source pill color (mapped client-side; see `SOURCE_MAP` in the file).

---

### `rank.html`

Private editorial feeder served from GitHub Pages.

- Gate: SHA-256-hashed password (baked into the file) plus a GitHub fine-grained PAT (entered once, persisted in `localStorage`).
- Loads `feed.xml`, `ratings.json`, `blocklist.json` and shows every item with a `<input type="range" min="0" max="5">` slider pre-filled from the current rating.
- On slider `change` event, updates the in-memory ratings, schedules a debounced (1s) commit.
- Commit path: GitHub Contents API `PUT /repos/{owner}/{repo}/contents/{ratings.json|blocklist.json}` with the cached SHA. On 409/422 (SHA conflict from a concurrent write), re-fetches SHA once and retries.
- Setting a slider to 5 appends the URL to the in-memory blocklist; moving it back below 5 removes it. The current pipeline run will drop blocklisted items from `feed.xml` on the next run.

---

### `ratings.json` and `blocklist.json`

- `ratings.json` — JSON object, keys are item URLs, values are integers 0–5. Absent URL implies 0. Only rank.html writes this file.
- `blocklist.json` — JSON array of URLs. Mirrors the set of rated-5 URLs but is the source of truth for the pipeline (which doesn't read ratings.json).

Both live at the repo root and are committed by the daily workflow alongside `feed.xml`.

---

## Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Set as GitHub Actions secret |
| `FEED_PATH` | No | `../feed.xml` | Path to write feed output |
| `STATE_PATH` | No | `./seen.json` | Path to dedup state file |
| `BLOCKLIST_PATH` | No | `../blocklist.json` | Path to read blocklist from |

---

## Failure Modes

**Fetch fails for a source** — logged, skipped, pipeline continues. Other sources unaffected.

**Claude API call fails for an item** — logged, item skipped. Item URL not added to seen.json, so it will retry next run.

**feed.xml missing or corrupt** — `load_existing_items` returns empty list and logs a warning. Pipeline continues; feed is rebuilt from scratch with only today's items.

**seen.json missing** — treated as empty. All items from all sources will be sent through the Claude filter on the next run. This is expensive but safe.

**blocklist.json missing** — treated as empty. Nothing is excluded.

**GitHub Actions fails to commit** — `feed.xml` and `seen.json` are not updated in the repo. Next run will re-process the same items. May produce duplicate feed entries. Investigate via the Actions tab in the repo.

**rank.html save fails (409/422)** — SHA mismatch from a concurrent write (e.g., another tab, or the pipeline writing at the same time). The page re-fetches the SHA and retries once. If it still fails, reloading the page is enough.

**PAT expired or revoked** — rank.html shows "Save failed" on every slider change. Generate a new fine-grained PAT with `Contents: read & write` on the `yaain` repo and replace it via the "Replace PAT" link in the footer.

---

## Constraints and Decisions

- Reddit is accessed without auth via the public JSON API. No credentials needed. Rate limit is generous for one daily run.
- The HN query is `claude+anthropic` — changing this changes what stories surface. Edit the `url` field in `sources.py`.
- Anthropic pages are scraped (no RSS). If Anthropic changes their page structure, `fetch_scrape` may return thin results. Check Anthropic sources first when the feed looks sparse.
- The filter uses Sonnet 4.6 for cost efficiency. Do not upgrade to Opus for filtering — it runs once per item across potentially 100+ items per day.
- `feed.xml` is now served via GitHub Pages alongside `index.html` and `rank.html`. The raw GitHub URL still works for RSS readers.
- The rank.html password gate is a soft lock; the real authorization is the fine-grained PAT. The password just keeps the page from looking inviting.
- Discord scraping is out of scope for v1.
