# YAAIN — Operations Guide

YAAIN watches the AI world for **things that change something we actually run**,
and publishes them six times a day. You don't need to touch it for it to work.

It used to be a Claude-news reader. Since 2026-08-30 it asks a different
question of every story it finds:

> Given the machines, models and tools we run — does this change what we can
> run, what it costs us in memory, whether we're *allowed* to use it, or
> whether something we depend on has broken?

Anything that can't name a specific thing of ours is thrown away.

---

## Where to read it

- **Homepage** — https://emteev.github.io/yaain/ — grouped by what each item asks of you.
- **RSS feed** — https://emteev.github.io/yaain/feed.xml — for any reader.
- **Ranker** — https://emteev.github.io/yaain/rank.html — yours only. Password + GitHub token.

## The three groups on the homepage

| Group | What it means |
|---|---|
| **Act on this** | Something we run is out of date, broken, restricted, or newly supported. A newer version of a model we run. A licence change. An outage. A dependency going unmaintained. |
| **Worth watching** | Something we *don't* run, that would fit our hardware, and might be worth having. |
| **Context** | Worth knowing, nothing to do. |

Every item carries a badge naming **the thing of ours it affects** — `Ollama`,
`LTX-2.3`, `bosun-brain`, and so on. That badge is the point: it's what makes
the page scannable in ten seconds.

## What changed about the ranker

**The homepage no longer waits for you.** It used to show *only* items you had
already rated, so anything unrated was invisible — which meant the page was
blank until you worked through the ranker, and would have frozen completely
the moment your token expired.

Now the machine's grouping lays the page out, and your rating sits on top of it:

| Your rating | Effect |
|---|---|
| unrated | still shown, in whichever group the machine put it |
| 1–4 | sorts to the top of its group |
| 5 | hidden permanently, and dropped from the feed (unchanged) |

So the ranker still does exactly what it did — it's just no longer the thing
standing between you and a working page. It also now shows you the machine's
verdict next to each item, so you're rating in context rather than blind to it.

⚠️ **The ranker's GitHub token expires and this has now happened three times.**
When it lapses the feed keeps updating and the homepage keeps working, but your
ratings silently stop saving. See "Decisions outstanding" below.

---

## The one file to keep current

`yaain/stack.json` lists what we run — every model, every tool, and the hard
limits (brownie's 16GB graphics memory, the licence rules, which versions are
pinned). **It is the whole basis on which YAAIN decides what matters.**

⚠️ **If you install something on brownie or the studio, or pin a tool to a
version, update that file.** If it drifts, YAAIN starts answering yesterday's
question — the exact problem it was rebuilt to solve.

## If something looks wrong

- **The homepage is stale.** Check the Actions tab: https://github.com/emteev/yaain/actions.
  The chief-of-staff watchdog also checks the published feed and will say so if
  it hasn't been rebuilt in 14 hours.
- **A source has gone quiet.** Every run prints which sources returned nothing.
- **Too much or too little is getting through.** That's the filter, and it is
  measurable — see `CLAUDE.md`, "Changing the filter prompt". Don't tune it by
  feel; the measurement is cheap and it has already caught one change that
  went the wrong way.

## What it costs

About **$2 a month** — one small Claude call per genuinely new item. It was
~$1/month before the rebuild; the increase is the wider source list. This is
below the noise floor of the weekly cost review, which is why it has never
appeared there.

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

**Feed hasn't updated**  
The chief-of-staff watchdog flags this by itself at 14 hours. Check the Actions tab. If the last run has a red X, click it and read the error. Common causes:
- `ANTHROPIC_API_KEY` expired or was revoked — replace it in repo Settings → Secrets and variables → Actions.
- A source URL changed or went down — every run prints which sources returned nothing, and continues with the rest.
- GitHub Actions was temporarily down — just re-run manually.

**Feed looks thin (very few items)**  
Usually the filter working. Most of what the sources publish genuinely doesn't touch anything we run, and roughly four items in five are meant to be thrown away. If it stays thin for a week, run `python yaain/bench.py --fetch --sample 120` (free — no API calls) to see which sources are still producing.

**A specific item is missing that should have been included**  
The filter rejected it, and there are two different reasons that need opposite fixes. Either the thing it affects isn't in `yaain/stack.json` (add it — that's the intended way to widen the net), or the wording of the filter's rules is too tight (that's a prompt change, and a prompt change must be measured — see `CLAUDE.md`).

**Titles look mashed together on the homepage**  
This was a bug in `fetch_scrape` (it grabbed entire Anthropic card text into the title). Fixed. If it returns, the fix is to prefer an inner heading element in the link; see `fetcher.py` → `fetch_scrape`.

**Duplicate items appearing**  
Usually means `seen.json` was reset (e.g., deleted). Self-corrects after one run.

**The homepage is missing something you rated**  
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

- Real-time alerts — this runs six times a day, it is not a monitoring tool.
- General AI news that touches nothing we run — the filter is built to reject it.
- The editorial AI beat — that is Hot Stacks' and Dark Frontier's ground, not this one's.
- Sentiment analysis, engagement scores, trending topics.
- Multi-user ranking. The ranker is single-editor by design.

---

## Key files at a glance

| File | What it does |
|---|---|
| `yaain/stack.json` | **What we run.** The basis for every relevance decision — keep it current |
| `yaain/sources.py` | Where the sources live |
| `yaain/bench.py` | Measures the filter before you change it |
| `yaain/seen.json` | Tracks what's already been processed — don't touch |
| `feed.xml` | The RSS output — don't touch |
| `ratings.json` | Your 0–5 ratings, keyed by URL — written by the ranker |
| `blocklist.json` | URLs to permanently exclude — grown when you rate 5 |
| `index.html` | The homepage. Edit to retune how the three groups are laid out |
| `rank.html` | The ranker. Edit to change the password hash |
| `.github/workflows/daily.yml` | The schedule (six times a day) — edit only to change run times |

---

## Decisions outstanding (yours)

1. **The ranker token.** Rather than regenerating it a fourth time, it could
   move off a browser-held token entirely — served from the Mini on the tailnet,
   committing with the Mini's existing key, the way our other editor tools work.
   That removes the expiring credential for good.
2. **Where it runs.** It stays on GitHub Actions: independent of the house,
   already working, ~$2/month. The honest counterweight is that this is metered
   API against a standing preference for local models — the filter *could* run
   free on the studio, at the cost of tailnet dependence and contention with
   Bosun's brain.
3. **Reddit.** r/LocalLLaMA is the best single source on VRAM-and-hardware
   reality and it returns 403 to everyone unauthenticated. Recovering it needs
   an approved Reddit API app — the same wall mac-hunter hit. Worth it?
4. **Scope.** YAAIN stays an internal engineering-intelligence tool, not an
   editorial AI beat (Hot Stacks and Dark Frontier already work that ground).
