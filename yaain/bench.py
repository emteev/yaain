"""
bench.py — measure the filter before shipping a change to it.

⚠️ WHY THIS EXISTS. Changing the filter prompt is an EXPERIMENT, not an edit.
Our books record twice (repo-hunter `projectfit`, 2026-08-21 and 08-22) that
adding rules to an already-tuned classification prompt can make it MORE
permissive rather than less — once tripling a fire rate with a five-line
bullet, and once leaving it perfectly inert. There is no way to know which
without measuring, on the SAME items, and reading the rows.

    # fetch a real batch once, cache it, spend nothing:
    python yaain/bench.py --fetch --sample 120

    # judge that batch and report:
    ANTHROPIC_API_KEY=... python yaain/bench.py --run --label new

    # judge the SAME batch with a variant prompt and compare:
    ANTHROPIC_API_KEY=... python yaain/bench.py --run --label old --old-prompt
    python yaain/bench.py --compare new old

It NEVER writes feed.xml, seen.json or blocklist.json. Measuring must not
change what a person sees.
"""

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict

import anthropic

import stack as stack_module
import filter as filter_module
from sources import SOURCES
from fetcher import fetch_all

HERE = os.path.dirname(__file__)
BATCH_PATH = os.path.join(HERE, "..", "bench", "batch.json")

# The pre-2026-08-30 prompt, kept verbatim so a comparison is against what
# actually ran, not a paraphrase of it.
OLD_PROMPT = """You are a strict content filter for a professional RSS feed.

The feed covers ONLY the Claude family of AI products made by Anthropic:
- Claude models (claude.ai, API, mobile)
- Claude Code (the CLI/agentic coding tool)
- Cowork (the desktop automation tool)
- Anthropic's research directly related to Claude
- Changes, updates, techniques, or discoveries that specifically affect how Claude tools work or can be used

You are NOT interested in:
- General AI news not specific to Claude
- Other AI products (GPT, Gemini, Llama, Mistral, etc.) unless directly compared to Claude in a useful way
- Opinion pieces without concrete Claude-specific information
- Hype, announcements of announcements, or vague "AI is changing everything" content
- Basic how-to content aimed at beginners (the audience is professional practitioners)

For each item, return a JSON object with this exact shape:
{
  "include": true | false,
  "summary": "2 sentences. What happened or what was discovered. Specific, factual, no filler.",
  "why": "1 sentence. What this means for someone using Claude tools professionally."
}

If include is false, summary and why should be empty strings.
Return ONLY the JSON object. No preamble, no explanation."""


def cmd_fetch(args):
    """Fetch a real batch and cache it. Costs nothing — no API calls."""
    print(f"Fetching {len(SOURCES)} sources...")
    items = fetch_all(SOURCES)
    print(f"  {len(items)} items")

    if args.sample and args.sample < len(items):
        # Stratified: take from every source in turn so no single source
        # dominates the sample and every source type is exercised.
        by_source = defaultdict(list)
        for it in items:
            by_source[it.get("source_name", "?")].append(it)
        rnd = random.Random(args.seed)
        for v in by_source.values():
            rnd.shuffle(v)
        picked, pools = [], list(by_source.values())
        i = 0
        while len(picked) < args.sample and any(pools):
            pool = pools[i % len(pools)]
            if pool:
                picked.append(pool.pop())
            i += 1
            if i > args.sample * 50:
                break
        items = picked
        print(f"  stratified sample: {len(items)} items from {len(by_source)} sources (seed {args.seed})")

    os.makedirs(os.path.dirname(BATCH_PATH), exist_ok=True)
    with open(BATCH_PATH, "w") as f:
        json.dump(items, f, indent=1)
    print(f"  wrote {BATCH_PATH}")
    print("  ⚠️ This batch file IS the sample definition — commit it, or the")
    print("     numbers below become unreproducible (the sources move nightly).")


def _results_path(label):
    return os.path.join(HERE, "..", "bench", f"results-{label}.jsonl")


def cmd_run(args):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    with open(BATCH_PATH) as f:
        items = json.load(f)

    stack = stack_module.load()
    client = anthropic.Anthropic(api_key=api_key)
    out_path = _results_path(args.label)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    n_fired = 0
    with open(out_path, "w") as out:
        for i, raw in enumerate(items, 1):
            item = dict(raw)
            title = item.get("title", "")
            rec = {
                "title": title,
                "url": item.get("url", ""),
                "source": item.get("source_name", ""),
                "verdict": "skip",
                "affects": "",
                "why": "",
            }
            try:
                if args.old_prompt:
                    rec.update(_judge_old(client, item))
                else:
                    kept = filter_module.judge_one(client, item, stack)
                    if kept:
                        rec["verdict"] = kept["verdict"]
                        rec["affects"] = kept.get("affects", "")
                        rec["why"] = kept.get("why", "")
            except Exception as e:
                rec["verdict"] = "error"
                rec["why"] = str(e)[:200]
            if rec["verdict"] not in ("skip", "error"):
                n_fired += 1
            out.write(json.dumps(rec) + "\n")
            out.flush()
            if i % 20 == 0:
                # flush: stdout to a file is block-buffered, so without this a
                # long run looks dead from outside while it is working fine.
                print(f"  {i}/{len(items)} judged ({n_fired} fired)", flush=True)

    print(f"\nwrote {out_path}")
    _report(args.label)


def _judge_old(client, item):
    """The pre-revival Claude-only gate, for a like-for-like comparison."""
    body = (item.get("body") or "").strip()
    user_content = (
        f"Source: {item.get('source_name','')}\n"
        f"Source context: {item.get('_source_notes','')}\n\n"
        f"Title: {item.get('title','')}\n\n"
        f"Body excerpt:\n{body[:1500] if body else '(no body text available)'}"
    )
    resp = client.messages.create(
        model=filter_module.MODEL, max_tokens=300,
        system=OLD_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    r = json.loads(raw)
    return {"verdict": "include" if r.get("include") else "skip", "why": r.get("why", "")}


def _load(label):
    with open(_results_path(label)) as f:
        return [json.loads(l) for l in f if l.strip()]


def _report(label):
    rows = _load(label)
    n = len(rows)
    tiers = Counter(r["verdict"] for r in rows)
    fired = sum(v for k, v in tiers.items() if k not in ("skip", "error"))
    print(f"\n── {label} ── {n} items")
    print(f"  FIRE RATE: {fired}/{n} = {100*fired/n:.1f}%")
    for k, v in tiers.most_common():
        print(f"    {k:<9} {v:>4}  ({100*v/n:.1f}%)")
    aff = Counter(r["affects"] for r in rows if r.get("affects"))
    if aff:
        print("  affects:")
        for k, v in aff.most_common(15):
            print(f"    {v:>3}  {k}")
    per_src = defaultdict(lambda: [0, 0])
    for r in rows:
        per_src[r["source"]][0] += 1
        if r["verdict"] not in ("skip", "error"):
            per_src[r["source"]][1] += 1
    print("  per source (judged / fired):")
    for src, (tot, f_) in sorted(per_src.items(), key=lambda kv: -kv[1][1]):
        print(f"    {tot:>3} / {f_:>3}  {src}")


def cmd_compare(args):
    a, b = _load(args.a), _load(args.b)
    fa = {r["url"] for r in a if r["verdict"] not in ("skip", "error")}
    fb = {r["url"] for r in b if r["verdict"] not in ("skip", "error")}
    print(f"── {args.a} vs {args.b} ── {len(a)} vs {len(b)} items")
    print(f"  {args.a} fires: {len(fa)}   {args.b} fires: {len(fb)}")
    print(f"  both: {len(fa & fb)}   only {args.a}: {len(fa - fb)}   only {args.b}: {len(fb - fa)}")
    if fa >= fb:
        print(f"  ⚠️ {args.a} is a strict SUPERSET of {args.b} — it only ever adds.")
    elif fb >= fa:
        print(f"  ⚠️ {args.b} is a strict SUPERSET of {args.a} — it only ever adds.")
    print(f"\n  fired by {args.a}, not by {args.b}:")
    for r in a:
        if r["url"] in (fa - fb):
            print(f"    [{r['verdict']:<7}] {r['title'][:76]}")
    print(f"\n  fired by {args.b}, not by {args.a}:")
    for r in b:
        if r["url"] in (fb - fa):
            print(f"    [{r['verdict']:<7}] {r['title'][:76]}")


def main():
    p = argparse.ArgumentParser(description="Measure the YAAIN filter. Never writes the feed.")
    p.add_argument("--fetch", action="store_true", help="fetch and cache a batch (free)")
    p.add_argument("--sample", type=int, default=0, help="stratified sample size")
    p.add_argument("--seed", type=int, default=20260831)
    p.add_argument("--run", action="store_true", help="judge the cached batch")
    p.add_argument("--label", default="new")
    p.add_argument("--old-prompt", action="store_true", help="judge with the pre-revival Claude-only prompt")
    p.add_argument("--report", metavar="LABEL", help="re-print a report from saved results")
    p.add_argument("--compare", nargs=2, metavar=("A", "B"))
    a = p.parse_args()

    if a.fetch:
        cmd_fetch(a)
    elif a.run:
        cmd_run(a)
    elif a.report:
        _report(a.report)
    elif a.compare:
        a.a, a.b = a.compare
        cmd_compare(a)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
