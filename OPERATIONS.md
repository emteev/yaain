# YAAIN — Operations Guide

YAAIN is a daily feed of Claude-specific signal, pulled from Reddit, Hacker News, Anthropic's own pages, and a handful of newsletters. It runs automatically every day at 8am ET. You don't need to touch it for it to work.

---

## The feed URL

```
https://raw.githubusercontent.com/emteev/yaain/main/feed.xml
```

Paste this into any RSS reader (NetNewsWire, Reeder, Feedly, etc.) to subscribe. The feed updates once daily. Each item includes a 2-sentence summary and a one-line note on why it matters.

---

## Checking if it ran

Go to the repo on GitHub → click the **Actions** tab. You'll see a list of runs. A green checkmark means it ran successfully and the feed was updated. A red X means something failed — see the troubleshooting section below.

The feed itself also has a "Last updated" timestamp at the top if you open `feed.xml` directly in the repo.

---

## Adding a source

Open `yaain/sources.py` in the repo. Each source looks like this:

```python
{
    "name": "Source Name",
    "type": "rss",
    "url": "https://example.com/feed",
    "notes": "What to include or exclude from this source.",
}
```

Append a new entry to the `SOURCES` list. The `type` must be one of: `rss`, `reddit`, `hn`, or `scrape`. The `notes` field is what tells the filter what to look for — be specific.

Commit the change. The new source will be picked up on the next daily run.

---

## Removing a source

In `yaain/sources.py`, delete or comment out the source's entry. Commit the change.

---

## Changing how strictly something is filtered

Edit the `notes` field for that source in `sources.py`. The notes are passed directly to Claude as instructions. More specific notes = tighter filtering. For example:

- Loose: `"General AI newsletter. Include if relevant to Claude."`
- Tight: `"Include only if the post describes a specific Claude Code feature, bug, or workflow discovery. Exclude opinion and general AI commentary."`

---

## Triggering a manual run

Go to the repo on GitHub → **Actions** tab → **Daily feed update** → **Run workflow** → **Run workflow**. The feed will update within a few minutes.

---

## Troubleshooting

**Feed hasn't updated in more than a day**
Check the Actions tab. If the last run has a red X, click it and read the error. Common causes:
- `ANTHROPIC_API_KEY` expired or was revoked — replace it in repo Settings → Secrets.
- A source URL changed or went down — the pipeline will log which source failed and continue with the rest.
- GitHub Actions was temporarily down — just re-run manually.

**Feed looks thin (very few items)**
The filter is working. Low-volume days are normal — Anthropic doesn't ship every day, and most Reddit posts don't clear the bar. If it stays thin for more than a week, check that the Anthropic scrape sources are still returning results (their page structure occasionally changes).

**A specific item is missing that should have been included**
The filter may have rejected it. The filter is intentionally strict — it passes only content specifically about Claude tools, not general AI content. If you want to widen the filter for a particular source, edit its `notes` field in `sources.py`.

**Duplicate items appearing**
This can happen if `seen.json` was reset (e.g., the file was accidentally deleted). It will self-correct after one run. If duplicates persist, file an issue or ask Claude to investigate `state.py`.

---

## What's out of scope (by design)

- Real-time alerts — this is a daily digest, not a monitoring tool.
- Content from non-Claude AI tools — the filter will reject it.
- Anthropic Discord — not included in v1.
- Sentiment analysis, engagement scores, trending topics.

---

## Key files at a glance

| File | What it does |
|---|---|
| `yaain/sources.py` | The only file you should normally edit |
| `yaain/seen.json` | Tracks what's already been processed — don't touch |
| `feed.xml` | The output — don't touch |
| `.github/workflows/daily.yml` | The daily schedule — edit only to change run time |
