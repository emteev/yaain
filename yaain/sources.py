"""
sources.py — all feed sources for YAAIN.

Each source is a dict with:
  name      : display name
  type      : 'rss' | 'reddit' | 'hn' | 'scrape'
  url       : endpoint
  notes     : optional context for the filter prompt
"""

SOURCES = [
    # ── Anthropic-native (100% signal by definition) ──────────────────────
    {
        "name": "Anthropic News",
        "type": "scrape",
        "url": "https://www.anthropic.com/news",
        "notes": "Anthropic's official news page. All content is relevant.",
    },
    {
        "name": "Anthropic Release Notes",
        "type": "scrape",
        "url": "https://support.claude.com/en/articles/12138966-release-notes",
        "notes": "Official Claude release notes. All content is relevant.",
    },
    {
        "name": "Claude Docs Changelog",
        "type": "scrape",
        "url": "https://docs.claude.com/en/release-notes/overview",
        "notes": "Claude API and docs changelog. All content is relevant.",
    },
    {
        "name": "Claude Code Docs",
        "type": "scrape",
        "url": "https://docs.claude.com/en/release-notes/claude-code",
        "notes": "Claude Code release notes. All content is relevant.",
    },
    {
        "name": "Anthropic Research Blog",
        "type": "scrape",
        "url": "https://www.anthropic.com/research",
        "notes": "Anthropic research publications. All content is relevant.",
    },

    # ── High-signal practitioner sources ──────────────────────────────────
    {
        "name": "Simon Willison's Blog",
        "type": "rss",
        "url": "https://simonwillison.net/atom/everything/",
        "notes": "Independent practitioner. Filter for Claude/Anthropic-specific content only.",
    },
    {
        "name": "Nathan Lambert — Interconnects",
        "type": "rss",
        "url": "https://www.interconnects.ai/feed",
        "notes": "ML researcher newsletter. Filter for Claude/Anthropic-specific content only.",
    },
    {
        "name": "Latent Space",
        "type": "rss",
        "url": "https://www.latent.space/feed",
        "notes": "AI practitioner podcast/newsletter. Filter for Claude/Anthropic-specific content only.",
    },

    # ── Other newsletters (low yield, tight filter) ────────────────────────
    {
        "name": "The AI Corner",
        "type": "rss",
        "url": "https://theaicorner.substack.com/feed",
        "notes": "General AI newsletter. Include only if specifically about Claude tools.",
    },
    {
        "name": "AI Maker",
        "type": "rss",
        "url": "https://aimaker.substack.com/feed",
        "notes": "General AI newsletter. Include only if specifically about Claude tools.",
    },

    # ── Reddit (mine carefully) ────────────────────────────────────────────
    {
        "name": "r/ClaudeAI",
        "type": "reddit",
        "url": "https://www.reddit.com/r/ClaudeAI/top.json?t=day&limit=25",
        "notes": "Dedicated Claude subreddit. Filter for substantive posts: discoveries, workarounds, real usage. Exclude rants, basic questions, memes.",
    },
    {
        "name": "r/ClaudeCode",
        "type": "reddit",
        "url": "https://www.reddit.com/r/ClaudeCode/top.json?t=day&limit=25",
        "notes": "Claude Code subreddit. Filter for substantive posts about Claude Code specifically.",
    },
    {
        "name": "r/LocalLLaMA",
        "type": "reddit",
        "url": "https://www.reddit.com/r/LocalLLaMA/top.json?t=day&limit=25",
        "notes": "Broader LLM community. Include only if specifically about Claude models or APIs.",
    },

    # ── Hacker News ────────────────────────────────────────────────────────
    {
        "name": "Hacker News",
        "type": "hn",
        "url": "https://hn.algolia.com/api/v1/search?query=claude+anthropic&tags=story&hitsPerPage=20&numericFilters=created_at_i>{}",
        "notes": "Filter for Claude/Anthropic-specific stories with substantive discussion. Min score 20.",
    },
]
