# bench — the measurement behind the 2026-08-30 filter

`batch.json` is a real, stratified, 120-item sample fetched from all 48 sources
on 2026-08-30 (seed 20260831 — bench.py's default). **It is committed because it IS the sample
definition** — the sources move nightly, so the same seed does not give the same
rows tomorrow, and without this file none of the numbers below can be checked.

Every variant below was judged on **these same 120 items**, so the comparisons
are paired rather than two separate draws.

| variant | fire rate | act | what changed |
|---|---|---|---|
| `v1` | 30.8% | 27 | first stack-driven prompt. `act` was 90% routine version bumps ("v0.31.1", "Patch release", "Update loader.py") |
| `v2` | 17.5% | 12 | sharpened `act` so a version number is not a consequence. **Strict subset of v1** — 16 removed, 0 added |
| `v3` | 31.7% | 28 | ⚠️ tried to make the act/watch boundary explicit. **Strict SUPERSET of v2 — +17, −0.** A rewrite intended to sharpen instead loosened it, past the v1 baseline |
| `v4` | 24.2% | 23 | **shipped.** Scoped the model-successor exemption so it cannot read as a general licence for tool releases. Neither a subset nor a superset — a reshaping (v3→v4: −11, +2) |

⚠️ **v3 is the finding worth keeping.** It reproduces, on a different model and
a different task, the repo-hunter `projectfit` result of 2026-08-21/22: adding
to a tuned classification prompt can make it *more* permissive, and there is no
way to know which without measuring. `bench.py --compare` prints a warning when
one variant is a strict superset of another, because that is the shape a
"tightening" takes when it has actually loosened.

Reproduce:

```bash
python yaain/bench.py --report v4
python yaain/bench.py --compare v3 v4
ANTHROPIC_API_KEY=... python yaain/bench.py --run --label mychange
```
