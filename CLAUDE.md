# YAAIN — Technical Reference

**Project:** Yet Another AI Newsletter
**Owner:** Em (Nothingworks)
**Purpose:** Watch the AI world for **changes that affect the stack we actually run**, and publish them tiered by what they demand of us.

It is *not* a general AI newsletter, and (since 2026-08-30) it is no longer a
Claude-release-notes reader. The relevance test is not a topic — it is
`yaain/stack.json`, the manifest of our own machines, models and tools.

**Automation:** GitHub Actions runs `yaain/main.py` on cron `0 0,4,8,12,16,20`
— **six times a day**, not daily. It commits `feed.xml`, `yaain/seen.json`,
`ratings.json` and `blocklist.json` back to `main`. GitHub Pages serves the
repo root at `https://emteev.github.io/yaain/`.

---

## The one file that matters

`yaain/stack.json` decides everything. It lists the machines we run on, the
models and tools we depend on, and the hard constraints (brownie's 16GB VRAM
wall, the licence policy, the torch ABI). The filter renders it into its own
prompt, so relevance is **data, not prose baked into a system message**.

⚠️ **It is only true if it is maintained.** Installing something on brownie or
the studio, or pinning/upgrading a tool, means updating `stack.json` in the
same breath. Otherwise this project decays into exactly the staleness it
exists to prevent.

---

## File map

```
yaain/
  main.py         Orchestrator. `YAAIN_DRY_RUN=1` fetches only — free, no API calls,
                  writes nothing. Use it to check source health and item volume.
  stack.json      THE MANIFEST. What we run. Edit this when the machines change.
  stack.py        Loads stack.json; renders it for the prompt; resolves a claimed
                  `affects` name onto a real stack item (or "" — see below).
  sources.py      Every source. Types: rss | hn | scrape | release_notes |
                  changelog_md | hf_org | page_digest. Optional per-source `limit`.
  fetcher.py      One handler per source type, dispatched via FETCH_FN.
  filter.py       The relevance gate. Returns verdict + affects + summary + why.
  feed.py         Reads/writes feed.xml (250 items). Also `touch_feed()` — the
                  heartbeat, see below.
  state.py        seen.json (5000 URLs), so nothing is judged twice.
  bench.py        Measure the filter before changing it. Never writes the feed.
  acceptance.py   The test that says whether the revival worked.
feed.xml          Generated. verdict/affects ride as <category domain="...">.
index.html        Homepage. Groups by verdict; ratings are an overlay.
rank.html         Private ranker. Password + GitHub token. Writes ratings/blocklist.
ratings.json      {url: 0–5}. blocklist.json  [url, …] (a 5 blocklists permanently).
bench/            The judged batch and its results — committed, because the batch
                  IS the sample definition and the sources move nightly.
```

⚠️ **A trap that was live until 2026-08-30 and must not return.** The repo held
a *second, different, never-executed* copy of every module at the root, newer
than the one the workflow ran. Improvements went into files nothing imported.
The duplicates are deleted; keep it that way — there is one pipeline, in
`yaain/`. (Same class as the Hot Stacks `source-reranker.csv` decoy: *the file
you edited was not the file in force.*)

---

## Verdicts

The filter returns one of four, and the homepage is laid out by them:

| verdict | means | shown as |
|---|---|---|
| `act` | something we already run is out of date, broken, restricted or newly supported | "Act on this" — full treatment |
| `watch` | a capability we do not run a version of, that would fit our hardware | "Worth watching" — cards |
| `context` | useful background, nothing to do | "Context" — one-line rows |
| `skip` | everything else — excluded from the feed entirely | — |

Two things are **enforced in code, not requested in the prompt** (`filter.py`):

1. An `act`/`watch` verdict must name a stack item that actually resolves via
   `stack.resolve()`. A verdict citing something we do not run is downgraded to
   `context`, not trusted.
2. Any unrecognised verdict string is an exclusion, never a pass.

## The feed is a heartbeat

`feed.py touch_feed()` re-stamps `<lastBuildDate>` even on a run that finds
nothing new. Without it, "ran and found nothing" and "stopped running" leave
identical traces, and the chief-of-staff watchdog (`watch/watchdog.py`,
`RSS_FRESHNESS`, 14h limit) could not tell them apart.

---

## Changing the filter prompt

⚠️ **This is an experiment, not an edit.** Our books record twice
(repo-hunter `projectfit`, 2026-08-21 and 08-22) that adding rules to an
already-tuned classification prompt can make it **more** permissive — once
tripling a fire rate, once leaving it perfectly inert. Prefer rewriting a rule
to appending one, and always measure:

```bash
python yaain/bench.py --fetch --sample 120          # free, caches the batch
ANTHROPIC_API_KEY=... python yaain/bench.py --run --label mychange
python yaain/bench.py --compare v3 mychange         # is it a superset?
ANTHROPIC_API_KEY=... python yaain/acceptance.py    # does it still catch the misses?
```

The comparison prints a warning when one variant is a strict **superset** of
the other — that is the shape a "tightening" takes when it has actually
loosened.

## Cost

~$2/month at the observed volume, dominated by the one Sonnet call per new
item. The system prompt is ~1.7K tokens and identical across a run, so it is
sent with `cache_control` — cost-only, and it cannot change a verdict.
