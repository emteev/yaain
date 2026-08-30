"""
filter.py — the relevance gate.

The question is NOT "is this about AI" or "is this about Claude". It is:

    given the stack we actually run, does this item change what we can run,
    what it costs us in VRAM, whether we are ALLOWED to use it, or whether
    something we depend on has broken or been deprecated?

The stack comes from stack.json (see stack.py) — data, not prose in a prompt —
so the day a machine changes, one file changes.

Each passing item is augmented with:
  verdict : "act" | "watch" | "context"
  affects : the canonical stack-item name it touches ("" for context)
  summary : 2 sentences (reused from the source when it has one, to save tokens)
  why     : 1 sentence — what it means for us specifically

⚠️ Two things are enforced in CODE, not hoped for in the prompt:
  1. An `act`/`watch` verdict must name a stack item that actually resolves.
     A verdict citing something we do not run is downgraded, not trusted.
  2. Any unknown verdict string is treated as an exclusion, never a pass.
"""

import json
import anthropic

import stack as stack_module

MODEL = "claude-sonnet-4-6"

# ── The prompt ────────────────────────────────────────────────────────────────
#
# ⚠️ CHANGING THIS IS AN EXPERIMENT, NOT AN EDIT. Our books record twice
# (repo-hunter projectfit, 2026-08-21/22) that adding rules to a tuned
# classification prompt can make it MORE permissive, not less — a five-line
# bullet once tripled a fire rate. Measure with `python yaain/bench.py` before
# and after, on the same items, and read the rows. Do not ship on the
# assumption that a longer prompt is a stricter one.
#
# The load-bearing move is the opening line: skip is the DEFAULT the model has
# to argue its way out of by naming a specific thing we run.

_INSTRUCTION = """You triage news for one small engineering operation. You are not
writing for a general audience — you are answering, for each item, one question:

    does this change anything for the stack described below?

START FROM `skip`. Only leave `skip` if you can name a specific item from the
lists above that this item actually affects. If you cannot name one, it is
`skip`, however interesting the item is.

VERDICTS

- "act"     — something we ALREADY RUN has changed in a way we would do
              something about. Exactly these:
              * a newer version, successor or new variant of a MODEL on the
                list — always, even when that particular repo is far too large
                for our machines, because a full-precision release is how a
                generation arrives, a quantisation follows within days, and
                being a generation behind is itself the thing to know;
              * a breaking change, removal, deprecation, outage or licence
                change in something on the list;
              * a tool of ours gaining support for a model or format we use;
              * a quantisation that brings something we want under 16GB;
              * something we depend on going unmaintained.
              ⚠️ A TOOL's version number is not one of those. "v2.1.251",
              "Patch release: v5.14.1", "v0.121.0", "Update loader.py", a
              dated list of app tweaks — a release of a tool we run is `skip`
              unless the item says what changed AND that change touches us.
              Being a tool we use every day does not earn an item `act`;
              saying something consequential does. (Models are the exception
              above: for a model, the new version IS the consequence.)
- "watch"   — something we DO NOT already run a version of: a new capability
              that would fit the hardware above (16GB VRAM on brownie, or the
              studio's memory) and that we might want. If we already run an
              earlier version of it, that is `act`, not `watch`. If we could
              not load it at all, that is `skip`.
- "context" — genuinely useful background for operating this stack: a
              technique, a benchmark, a licensing or hardware development that
              changes how we should think, without a specific item to act on.
- "skip"    — everything else. General AI industry news, funding, product
              launches for things we do not run, opinion, hype, anything
              needing hardware we do not have.

`affects` MUST be one of the names listed above, copied exactly. For `context`,
leave it empty. Do not invent a name; a verdict naming something absent from
those lists will be discarded.

Weigh it as we would: a licence restriction is decisive, a VRAM figure over
16GB is disqualifying for brownie, and a version bump on a model we actually
run matters more than a better model we cannot load.

Return ONLY this JSON object:
{
  "verdict": "act" | "watch" | "context" | "skip",
  "affects": "exact name from the lists above, or empty string",
  %s
  "why": "1 sentence. What this specifically means for THIS operation — name the consequence, not the announcement."
}
Return ONLY the JSON. No preamble."""

_SUMMARY_FIELD = '"summary": "2 sentences. What actually changed. Specific and factual — versions, sizes, licences, numbers. No filler.",'
_NO_SUMMARY_FIELD = ""

VALID_VERDICTS = {"act", "watch", "context"}


def build_system_prompt(stack: dict, want_summary: bool) -> str:
    return (
        stack_module.render(stack)
        + "\n\n"
        + (_INSTRUCTION % (_SUMMARY_FIELD if want_summary else _NO_SUMMARY_FIELD))
    )


def judge_one(client, item: dict, stack: dict) -> dict | None:
    """
    Judge a single item. Returns the augmented item, or None if excluded.
    Pure of side effects on anything but `item`, so bench.py can reuse it.
    """
    title = item.get("title", "").strip()
    if not title:
        return None

    extracted_summary = (item.get("summary") or "").strip()
    want_summary = not extracted_summary

    body = (item.get("body") or "").strip()
    user_content = (
        f"Source: {item.get('source_name', '')}\n"
        f"Source context: {item.get('_source_notes', '')}\n\n"
        f"Title: {title}\n\n"
        f"Body excerpt:\n{body[:1500] if body else '(no body text available)'}"
    )

    # The system prompt is identical for every item in a run and is ~1.7K
    # tokens, so it is cached. Caching is COST-ONLY: `cache_control` is
    # stripped by the API before the model sees the prompt, so this cannot
    # change a verdict. (playbook: "Add prompt caching to an agent's tool-loop")
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=[{
            "type": "text",
            "text": build_system_prompt(stack, want_summary),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    result = json.loads(raw)

    verdict = (result.get("verdict") or "").strip().lower()
    # An unknown verdict is an exclusion. Never let a malformed reply pass.
    if verdict not in VALID_VERDICTS:
        return None

    affects = stack_module.resolve(stack, result.get("affects", ""))

    # ENFORCED, not requested: act/watch must name something we actually run.
    # A confident verdict about a thing absent from the stack is a claim that
    # failed its own test, so it drops to context rather than being trusted.
    if verdict in ("act", "watch") and not affects:
        verdict = "context"

    item["verdict"] = verdict
    item["affects"] = affects
    item["summary"] = extracted_summary if extracted_summary else result.get("summary", "")
    item["why"] = result.get("why", "")
    item.pop("_source_notes", None)
    item.pop("body", None)
    return item


def filter_items(items: list[dict], api_key: str, stack: dict | None = None) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)
    stack = stack if stack is not None else stack_module.load()
    passed = []
    for item in items:
        title = item.get("title", "").strip()
        try:
            kept = judge_one(client, item, stack)
        except Exception as e:
            print(f"    [filter error] {title[:50]}: {e}")
            continue
        if kept:
            passed.append(kept)
            tag = {"act": "!", "watch": "~", "context": "·"}[kept["verdict"]]
            aff = f" [{kept['affects']}]" if kept["affects"] else ""
            print(f"    {tag} {title[:62]}{aff}")
        else:
            print(f"    ✗ {title[:70]}")
    return passed
