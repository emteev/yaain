"""
acceptance.py — the test that says whether the revival worked.

    ANTHROPIC_API_KEY=... python yaain/acceptance.py

⚠️ The bar, set before any of this was built: if the rebuilt YAAIN cannot
surface the three misses that justified rebuilding it, it is not done. Those
misses (measured 2026-08-30) were:

    we run          the world had              and nothing of ours said so
    qwen3.6         Qwen3.8-27B   (2026-08-13)
    LTX-2.3         LTX-2.5       (2026-08-10)   — behind the DAY AFTER we installed it

⚠️ The review listed a THIRD miss, `tencent/Hy4-preview` against our Hunyuan3D
2.0. Checked 2026-08-30 against the HF API: Hy4-preview is a 780B
`text-generation` model — a Tencent LLM, not a 3D model. The review matched on
the name. Tencent's real successor line is `Hunyuan3D-2.1`, published
2025-06-13, i.e. a year old and predating our deliberate choice of 2.0. So it
is not a case this test can hold, and it is not re-added.

This builds each of those items through the REAL fetch path (the same HF API
call `hf_org` makes) and judges them with the REAL filter, so a pass means the
shipped code catches them — not that a hand-written fixture does.

A pass is: verdict `act`, naming the stack item it supersedes.
"""

import os
import sys

import anthropic

import stack as stack_module
import filter as filter_module
from fetcher import fetch_hf_org

# (HF org, substring identifying the model, the stack item it should name)
#
# ⚠️ THE QWEN CASE WENT HISTORICAL ON 2026-09-12. It was written as "we run
# qwen3.6, the world has Qwen3.8, and nothing of ours said so" — then we took
# the upgrade, so the stack item it must name changed from `qwen3.6` to
# `qwen3.8` (the manifest keeps qwen3.6 as an alias, and `resolve` returns the
# canonical name). What it still proves is real but smaller: the live HF fetch,
# the alias resolution and the `act` path all work end to end. It no longer
# proves the filter catches a generation we are BEHIND on.
#
# LTX-2.5 now carries that bar alone — we run LTX-2.3, and 2.5 shipped the day
# after we installed 2.3. When we take LTX-2.5, this test needs a new live case
# rather than a third historical one; do not let it decay into two tests that
# can only pass.
CASES = [
    ("Qwen",       "Qwen3.8",     "qwen3.8"),
    ("Lightricks", "LTX-2.5",     "LTX-2.3"),
]
# ⚠️ RAISED 4 → 20 on 2026-09-14, because at 4 THIS TEST WAS FAILING ITS OWN
# HEADLINE CASE and nobody was running it to notice. `hf_org` returns newest
# first; Lightricks published NINE LTX-2.5 LoRAs through August and September,
# which pushed the base `Lightricks/LTX-2.5` repo — the entire point of the
# case — down to position 11, outside a 4-item window. The test judged four
# LoRAs, they were skipped, and it reported that the filter had missed LTX-2.5.
# The filter had not; the test never showed it the item.
#
# A real run judges every new item an org publishes, so the faithful test does
# too. 20 covers every variant either org has ever shipped in one generation
# with room to spare, at a cost of a few cents per run.
MAX_JUDGED = 20


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    stack = stack_module.load()
    client = anthropic.Anthropic(api_key=api_key)

    failures = []
    for org, needle, expected in CASES:
        # Pull a generous window so the target is present regardless of how much
        # the org has shipped since. This is the real fetcher, not a fixture.
        items = fetch_hf_org({"name": f"HF — {org}", "type": "hf_org",
                              "url": org, "limit": 60, "notes": ""})
        hits = [i for i in items if needle.lower() in i["title"].lower()]
        if not hits:
            print(f"  ?  {needle}: not in {org}'s latest 60 — cannot test "
                  f"(it may have aged out; widen the limit or update the case)")
            failures.append(f"{needle}: not found")
            continue

        # A real run judges EVERY variant an org publishes, so the test does
        # too: the release is caught if ANY of its repos is flagged. Judging
        # one hand-picked variant would test my choice of variant, not the
        # filter.
        ok, seen = False, []
        for item in hits[:MAX_JUDGED]:
            item = dict(item)
            item["_source_notes"] = f"New models published by the {org} org on Hugging Face."
            judged = filter_module.judge_one(client, item, stack)
            verdict = judged["verdict"] if judged else "skip"
            affects = judged.get("affects", "") if judged else ""
            hit = verdict == "act" and affects == expected
            ok = ok or hit
            seen.append((hit, item["title"], verdict, affects,
                         judged.get("why", "") if judged else ""))

        print(f"  {'PASS' if ok else 'FAIL'}  {needle} vs {expected} "
              f"({len(hits)} repos, judged {min(len(hits), MAX_JUDGED)})")
        for hit, title, verdict, affects, why in seen:
            print(f"        {'✓' if hit else ' '} {verdict:<7} {affects or '-':<12} {title[24:76]}")
            if hit and why:
                print(f"          why: {why[:140]}")
        if not ok:
            failures.append(f"{needle}: nothing reached act/{expected}")

    print()
    if failures:
        print(f"ACCEPTANCE FAILED — {len(failures)} of {len(CASES)}: {'; '.join(failures)}")
        sys.exit(1)
    print(f"ACCEPTANCE PASSED — all {len(CASES)} known misses surfaced as `act`.")


if __name__ == "__main__":
    main()
