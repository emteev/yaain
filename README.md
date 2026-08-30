# YAAIN

*Yet Another AI Newsletter* — but it isn't a newsletter about AI.

It watches ~48 sources and asks one question of everything it finds:

> Given the machines, models and tools **we actually run**, does this change
> what we can run, what it costs us in memory, whether we're *allowed* to use
> it, or whether something we depend on has broken?

Anything that can't name a specific thing of ours is thrown away. What's left
is grouped by what it demands — **act** / **watch** / **context** — and tagged
with the thing it affects.

- **Read it:** https://emteev.github.io/yaain/
- **Subscribe:** https://emteev.github.io/yaain/feed.xml
- **How it works / how to change it:** [CLAUDE.md](CLAUDE.md)
- **How to run it:** [OPERATIONS.md](OPERATIONS.md)

The list of what we run lives in [`yaain/stack.json`](yaain/stack.json). It is
the whole basis of every relevance decision, and it is only true if it is kept
current.
