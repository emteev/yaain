"""
stack.py — loads stack.json and renders it for the filter prompt.

stack.json is the manifest of what we actually run. It is the ONLY thing that
decides relevance, which is why it is data rather than prose baked into a
prompt: when the machines change, one file changes.

Also exposes the set of valid stack-item names, so the filter can ENFORCE that
a verdict names a real thing rather than inventing one. Model judges, code
enforces.
"""

import json
import os

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "stack.json")


def load(path: str = DEFAULT_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def item_names(stack: dict) -> set[str]:
    """Every name a verdict is allowed to cite, lowercased."""
    names = set()
    for entry in stack.get("models", []) + stack.get("tools", []):
        names.add(entry["name"].lower())
        for alias in entry.get("aliases", []):
            names.add(alias.lower())
    for m in stack.get("machines", []):
        names.add(m["name"].lower())
    return names


def resolve(stack: dict, claimed: str) -> str:
    """
    Map a model-supplied 'affects' string onto a canonical stack-item name.
    Returns "" if it matches nothing we run — which the filter treats as a
    failed claim, not a pass.
    """
    if not claimed:
        return ""
    c = claimed.strip().lower()
    for entry in stack.get("models", []) + stack.get("tools", []):
        if c == entry["name"].lower():
            return entry["name"]
        for alias in entry.get("aliases", []):
            if c == alias.lower():
                return entry["name"]
    # Substring fallback: "Ollama 0.33" -> "Ollama". Longest alias wins so
    # "qwen2.5-vl" beats "qwen2.5".
    best, best_len = "", 0
    for entry in stack.get("models", []) + stack.get("tools", []):
        for alias in [entry["name"]] + entry.get("aliases", []):
            a = alias.lower()
            if len(a) > best_len and (a in c or c in a):
                best, best_len = entry["name"], len(a)
    for m in stack.get("machines", []):
        if m["name"].lower() == c:
            return m["name"]
    return best


def render(stack: dict) -> str:
    """A compact text rendering of the stack for the system prompt.

    ⚠️ DELIBERATELY DOES NOT RENDER THE `chosen` BLOCKS. They are for a human
    (and for the alerting digest) deciding whether a new thing supersedes an old
    decision — not for the filter deciding relevance. Feeding them in would grow
    the prompt by roughly a third, and OUR OWN BOOKS RECORD TWICE that editing a
    tuned classification prompt moves it in ways nobody predicts (repo-hunter
    projectfit 2026-08-21/22; this filter's own v3, which loosened while trying
    to tighten). If you want them in the prompt, that is an EXPERIMENT: measure
    it on the pinned batch with `bench.py --compare` before shipping it.
    """
    lines = []

    lines.append("MACHINES WE RUN ON:")
    for m in stack.get("machines", []):
        ceiling = f" — {m['ceiling']}" if m.get("ceiling") else ""
        lines.append(f"- {m['name']}: {m['role']}. {m['hardware']}{ceiling}")

    lines.append("")
    lines.append("MODELS WE RUN (cite the name in `affects`; also-known-as names")
    lines.append("count as the same thing, including newer versions of it):")
    for e in stack.get("models", []):
        aka = ", ".join(e.get("aliases", []))
        lines.append(f"- {e['name']} [on {e['runs_on']}] — {e['detail']} Used by: {e['used_by']}"
                     + (f" [also: {aka}]" if aka else ""))

    lines.append("")
    lines.append("TOOLS WE DEPEND ON (cite the name in `affects`; also-known-as")
    lines.append("names count as the same thing):")
    for e in stack.get("tools", []):
        flag = " [CRITICAL]" if e.get("critical") else ""
        aka = ", ".join(e.get("aliases", []))
        lines.append(f"- {e['name']}{flag} — {e['detail']}" + (f" [also: {aka}]" if aka else ""))

    lines.append("")
    lines.append("HARD CONSTRAINTS:")
    for c in stack.get("constraints", []):
        lines.append(f"- {c}")

    return "\n".join(lines)
