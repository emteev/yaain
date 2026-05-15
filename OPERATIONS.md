# YAAIN — Operations Guide

YAAIN is a daily feed of Claude-specific signal, pulled from Reddit, Hacker News, Anthropic's own pages, and a handful of newsletters. It runs automatically every day at 8am ET. You don't need to touch it for it to work.

There are three ways to read it:

- **Homepage** — `https://emteev.github.io/yaain/` — items you've ranked, laid out by importance. Auto-refreshes every 5 minutes.
- **RSS feed** — `https://raw.githubusercontent.com/emteev/yaain/main/feed.xml` — every passing item, for any RSS reader.
- **Ranker** — `https://emteev.github.io/yaain/rank.html` — you only. Password + GitHub token. Drag a slider next to any item to set its rank; auto-saves.

---

## The homepage

Items rated 1–4 appear; items rated 0 or 5 are hidden.

| Rank | Where it appears |
|---|---|
| 0 | Hidden (default for unrated items) |
| 1 | Hero — full-width headline across the top, summary + why, byline |
| 2 | Featured — two-column band, headline + one paragraph |
| 3 | Brief — four-column band, short summary |
| 4 | Bullet — headline · publication · date |
| 5 | Deleted — added to the blocklist; removed from the RSS feed on the next pipeline run |

The page polls every 5 minutes. If you rate something, give it ~1 minute to land on GitHub, then reload the homepage (or wait for the auto-poll).

---

## Ranking items

1. Open `https://emteev.github.io/yaain/rank.html`
2. First time on this browser: type your password (`Sh*8#m-_n$3R`) and paste your GitHub personal access token (PAT). Both get saved in this browser's storage. You won't be asked again unless you clear the browser or click "Lock" / "Replace PAT" in the footer.
3. Drag the slider next to any item to set its rank, 0 to 5. The save fires when you release the slider. The pill at top-right flashes "Saving…" then "Saved ✓".

Notes:

- Setting a slider to **5** drops the item from the next-day RSS feed too, not just the homepage. Move it back below 5 to un-block.
- The PAT is what authorizes writes. The password is just a soft lock on the page itself.
- The PAT can expire; if "Save failed" appears repeatedly, see "Renewing the PAT" in troubleshooting.

---

## Subscribing to the RSS feed

Paste this into any RSS reader (NetNewsWire, Reeder, Feedly, etc.):

```
https://raw.githubusercontent.com/emteev/yaain/main/feed.xml
```

Each item includes a 2-sentence summary and a one-line note on why it matters. Items you've rated 5 are excluded from the feed.

---

## Checking if it ran

Go to the repo on GitHub → click the **Actions** tab. A green checkmark on the latest "Daily feed update" means the pipeline ran successfully. A red X means something failed — see troubleshooting below.

The feed itself has a "Last updated" timestamp at the top of `feed.xml`.

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

Append a new entry to the `SOURCES` list. `type` must be one of: `rss`, `reddit`, `hn`, or `scrape`. `notes` is what tells the filter what to look for — be specific. Commit. The new source is picked up on the next daily run.

---

## Removing a source

In `yaain/sources.py`, delete or comment out the source's entry. Commit. Already-fetched items from that source stay in `feed.xml` until they age out.

---

## Changing how strictly something is filtered

Edit the `notes` field for that source in `sources.py`. The notes are passed directly to Claude as instructions. More specific notes = tighter filtering.

- Loose: `"General AI newsletter. Include if relevant to Claude."`
- Tight: `"Include only if the post describes a specific Claude Code feature, bug, or workflow discovery. Exclude opinion and general AI commentary."`

---

## Triggering a manual run

Repo on GitHub → **Actions** tab → **Daily feed update** (in left sidebar, not in the run list) → **Run workflow** button → green confirm. The feed updates within a minute or two.

---

## Initial setup (one-time)

You only need to do this once per machine.

### 1. Pages

Repo Settings → Pages → "Build and deployment" → Source: **Deploy from a branch** → Branch: `main`, folder: `/ (root)` → Save. Site goes live at `https://emteev.github.io/yaain/` within a minute. The repo must be public for free GitHub Pages.

### 2. Set the ranker password

Pick a password. Hash it in Terminal:

```sh
echo -n "yourpassword" | shasum -a 256
```

Open `rank.html` on GitHub, click the pencil to edit, find the `PASSWORD_SHA256 = "…"` line near the top of the script (around line 239), replace the hex string between the quotes. Commit.

### 3. Generate a GitHub personal access token

GitHub → click your profile picture (top right) → **Settings** → **Developer settings** (bottom of left sidebar) → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.

- Name: anything
- Resource owner: your account
- Repository access: **Only select repositories** → `yaain`
- Repository permissions → expand → **Contents** → **Read and write**
- Generate. **Copy the token immediately** — GitHub only shows it once. Save it to a password manager.

### 4. Unlock the ranker

Open `https://emteev.github.io/yaain/rank.html`. Type your password. Paste the token. Click Unlock. Both are stored in this browser only and only sent to `api.github.com`.

---

## Troubleshooting

**Feed hasn't updated in more than a day**  
Check the Actions tab. If the last run has a red X, click it and read the error. Common causes:
- `ANTHROPIC_API_KEY` expired or was revoked — replace it in repo Settings → Secrets and variables → Actions.
- A source URL changed or went down — the pipeline logs which source failed and continues with the rest.
- GitHub Actions was temporarily down — just re-run manually.

**Feed looks thin (very few items)**  
The filter is working. Low-volume days are normal — Anthropic doesn't ship every day, and most Reddit posts don't clear the bar. If it stays thin for more than a week, check that the Anthropic scrape sources are still returning results (their page structure occasionally changes).

**A specific item is missing that should have been included**  
The filter may have rejected it. The filter is intentionally strict — it passes only content specifically about Claude tools, not general AI content. To widen for a source, edit its `notes` field in `sources.py`.

**Titles look mashed together on the homepage**  
This was a bug in `fetch_scrape` (it grabbed entire Anthropic card text into the title). Fixed. If it returns, the fix is to prefer an inner heading element in the link; see `fetcher.py` → `fetch_scrape`.

**Duplicate items appearing**  
Usually means `seen.json` was reset (e.g., deleted). Self-corrects after one run.

**The homepage shows "Nothing rated for the homepage yet" even though you rated things**  
Two likely causes. First, GitHub's CDN can lag ~30–60s behind a commit — wait, then hard-refresh (Cmd-Shift-R). Second, the URL key the ranker saves might not exactly match the URL the homepage reads from `feed.xml`. Open `https://emteev.github.io/yaain/ratings.json` and `feed.xml` in two tabs and compare a URL from each — they should match exactly.

**Ranker says "Save failed"**  
The PAT is the usual suspect. See "Renewing the PAT" below. Other 422/409 errors are SHA conflicts — the ranker auto-retries once; if it keeps failing, reload the page.

**Renewing the PAT**  
PATs expire on the schedule you picked at creation. To renew:
1. GitHub → profile photo → Settings → Developer settings → Personal access tokens → Fine-grained
2. Find the old token, revoke it (housekeeping)
3. Generate a new one with the same settings (Contents: read & write on `yaain`)
4. Open the ranker → click "Replace PAT" in the footer → paste the new token

**Forgot the ranker password**  
You set the SHA-256 hash yourself, so it can't be recovered. Pick a new one and re-do step 2 of initial setup.

---

## What's out of scope (by design)

- Real-time alerts — this is a daily digest, not a monitoring tool.
- Content from non-Claude AI tools — the filter will reject it.
- Anthropic Discord — not included in v1.
- Sentiment analysis, engagement scores, trending topics.
- Multi-user ranking. The ranker is single-editor by design.

---

## Key files at a glance

| File | What it does |
|---|---|
| `yaain/sources.py` | The only Python file you should normally edit |
| `yaain/seen.json` | Tracks what's already been processed — don't touch |
| `feed.xml` | The RSS output — don't touch |
| `ratings.json` | Your 0–5 ratings, keyed by URL — written by the ranker |
| `blocklist.json` | URLs to permanently exclude — grown when you rate 5 |
| `index.html` | The homepage. Edit if you want to retune the tier layouts |
| `rank.html` | The ranker. Edit to change the password hash |
| `.github/workflows/daily.yml` | The daily schedule — edit only to change run time |
