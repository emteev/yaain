"""
sources.py — all feed sources for YAAIN.

Each source is a dict with:
  name      : display name
  type      : 'rss' | 'reddit' | 'hn' | 'scrape' | 'release_notes' | 'changelog_md'
  url       : endpoint
  notes     : short description of what the source is (no exclusion rules —
              the filter prompt handles topic gating)
"""

SOURCES = [
    # ── Anthropic-native ──────────────────────────────────────────────────────
    {
        "name": "Anthropic News",
        "type": "scrape",
        "url": "https://www.anthropic.com/news",
        "notes": "Anthropic's official news page.",
    },
    {
        "name": "Anthropic Engineering",
        "type": "scrape",
        "url": "https://www.anthropic.com/engineering",
        "notes": "Anthropic's engineering blog — technical writeups and deep dives.",
    },
    {
        "name": "Anthropic Research Blog",
        "type": "scrape",
        "url": "https://www.anthropic.com/research",
        "notes": "Anthropic research publications.",
    },
    {
        "name": "Anthropic Release Notes",
        "type": "release_notes",
        "url": "https://support.claude.com/en/articles/12138966-release-notes",
        "notes": "Official Claude release notes.",
    },
    {
        "name": "Claude Docs Changelog",
        "type": "scrape",
        "url": "https://docs.claude.com/en/release-notes/overview",
        "notes": "Claude API and docs changelog.",
    },
    {
        "name": "Claude Code Changelog",
        "type": "changelog_md",
        "url": "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md",
        "notes": "Claude Code version changelog.",
    },
    {
        "name": "Anthropic Status",
        "type": "rss",
        "url": "https://status.anthropic.com/history.atom",
        "notes": "Anthropic status page — incidents, postmortems, deprecations.",
    },

    # ── GitHub releases / commits (atom feeds) ───────────────────────────────
    {
        "name": "Claude Code Releases",
        "type": "rss",
        "url": "https://github.com/anthropics/claude-code/releases.atom",
        "notes": "GitHub releases for the Claude Code CLI.",
    },
    {
        "name": "Anthropic Python SDK Releases",
        "type": "rss",
        "url": "https://github.com/anthropics/anthropic-sdk-python/releases.atom",
        "notes": "GitHub releases for the official Anthropic Python SDK.",
    },
    {
        "name": "Anthropic TypeScript SDK Releases",
        "type": "rss",
        "url": "https://github.com/anthropics/anthropic-sdk-typescript/releases.atom",
        "notes": "GitHub releases for the official Anthropic TypeScript SDK.",
    },
    {
        "name": "Anthropic Cookbook Commits",
        "type": "rss",
        "url": "https://github.com/anthropics/anthropic-cookbook/commits/main.atom",
        "notes": "New examples and patterns added to the official Anthropic cookbook.",
    },

    # ── High-signal practitioner sources ─────────────────────────────────────
    {
        "name": "Simon Willison's Blog",
        "type": "rss",
        "url": "https://simonwillison.net/atom/everything/",
        "notes": "Independent practitioner who writes frequently about Claude.",
    },
    {
        "name": "Nathan Lambert — Interconnects",
        "type": "rss",
        "url": "https://www.interconnects.ai/feed",
        "notes": "ML researcher newsletter; often covers Anthropic.",
    },
    {
        "name": "Latent Space",
        "type": "rss",
        "url": "https://www.latent.space/feed",
        "notes": "AI practitioner podcast and newsletter.",
    },
    {
        "name": "AI Maker",
        "type": "rss",
        "url": "https://aimaker.substack.com/feed",
        "notes": "General AI newsletter.",
    },

    # ── Reddit ────────────────────────────────────────────────────────────────
    {
        "name": "r/ClaudeAI",
        "type": "reddit",
        "url": "https://www.reddit.com/r/ClaudeAI/top.json?t=week&limit=25",
        "notes": "Dedicated Claude subreddit — top of the week.",
    },
    {
        "name": "r/ClaudeCode",
        "type": "reddit",
        "url": "https://www.reddit.com/r/ClaudeCode/top.json?t=week&limit=25",
        "notes": "Claude Code subreddit — top of the week.",
    },
    {
        "name": "r/LocalLLaMA",
        "type": "reddit",
        "url": "https://www.reddit.com/r/LocalLLaMA/top.json?t=week&limit=25",
        "notes": "Broader LLM community; filter catches the Claude-relevant posts.",
    },

    # ── Hacker News ───────────────────────────────────────────────────────────
    {
        "name": "Hacker News — claude",
        "type": "hn",
        "url": "https://hn.algolia.com/api/v1/search?query=claude&tags=story&hitsPerPage=25&numericFilters=created_at_i>{}",
        "notes": "HN stories matching 'claude'.",
    },
    {
        "name": "Hacker News — anthropic",
        "type": "hn",
        "url": "https://hn.algolia.com/api/v1/search?query=anthropic&tags=story&hitsPerPage=25&numericFilters=created_at_i>{}",
        "notes": "HN stories matching 'anthropic'.",
    },
]
