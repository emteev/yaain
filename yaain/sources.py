"""
sources.py — every source YAAIN watches.

Each source is a dict with:
  name   : display name
  type   : 'rss' | 'hn' | 'scrape' | 'release_notes' | 'changelog_md'
           | 'hf_org' | 'page_digest'
  url    : endpoint (for hf_org: the Hugging Face ORG NAME)
  limit  : optional per-source item cap (rss + hf_org). Noisy feeds cap
           themselves so one source cannot eat a run's API budget.
  notes  : what the source is. NO exclusion rules here — relevance is decided
           by stack.json + the filter prompt, in one place.

⚠️ Every feed below was fetched and dated. Re-verify before trusting: feeds
rot, and a feed rotting silently is the entire premise of this project.
Verified 2026-08-30 unless noted.

⚠️ A 200 IS NOT FRESHNESS. `qwenlm.github.io/blog/index.xml` and
`semianalysis.com/feed` both return 200 and are a YEAR stale — check the newest
item's date on anything you add. Verified dead, do not re-chase: all Reddit
(403, needs an approved API app), `blog.comfy.org/rss.xml` (404 — the working
path is `/feed`), Mistral, The Batch, `unsloth.ai/blog` (403 Cloudflare),
`anthropic.com/rss.xml` (404 — Anthropic publishes no RSS, hence the scrapes).
"""

SOURCES = [
    # ── Tier 1: the tools we actually run ────────────────────────────────────
    # Highest signal per item. When one of these breaks or ships a fix, it
    # changes what we can do that day.
    {
        "name": "llama.cpp releases",
        "type": "rss",
        "url": "https://github.com/ggml-org/llama.cpp/releases.atom",
        "limit": 10,
        "notes": "The GGUF lineage every quantised model we run depends on.",
    },
    {
        "name": "Ollama releases",
        "type": "rss",
        "url": "https://github.com/ollama/ollama/releases.atom",
        "limit": 10,
        "notes": "Serves every model on the studio, incl. bosun-brain.",
    },
    {
        "name": "Ollama blog",
        "type": "rss",
        "url": "https://ollama.com/blog/rss.xml",
        "limit": 10,
        "notes": "New model support, context and keep-alive behaviour.",
    },
    {
        "name": "ComfyUI releases",
        "type": "rss",
        "url": "https://github.com/comfyanonymous/ComfyUI/releases.atom",
        "limit": 10,
        "notes": "brownie's generation front end.",
    },
    {
        "name": "Comfy Org blog",
        "type": "rss",
        "url": "https://blog.comfy.org/feed",
        "limit": 10,
        "notes": "New node packs and day-one model support in ComfyUI.",
    },
    {
        "name": "transformers releases",
        "type": "rss",
        "url": "https://github.com/huggingface/transformers/releases.atom",
        "limit": 8,
        "notes": "brownie's vision tier runs directly on transformers.",
    },
    {
        "name": "Claude Code releases",
        "type": "rss",
        "url": "https://github.com/anthropics/claude-code/releases.atom",
        "limit": 10,
        "notes": "The agent this operation is built in.",
    },
    {
        "name": "Hermes Agent releases",
        "type": "rss",
        "url": "https://github.com/NousResearch/hermes-agent/releases.atom",
        "limit": 8,
        "notes": "We run v0.20.1 PINNED. A release is news precisely because we will NOT take it automatically.",
    },
    {
        "name": "trellis.cpp releases",
        "type": "rss",
        "url": "https://github.com/pwilkin/trellis.cpp/releases.atom",
        "limit": 8,
        "notes": "Our licence-clean image-to-3D path on brownie.",
    },
    {
        "name": "ComfyUI-GGUF commits",
        "type": "rss",
        "url": "https://github.com/city96/ComfyUI-GGUF/commits/main.atom",
        "limit": 8,
        "notes": "Provides UnetLoaderGGUF — the ONLY way our LTX-2.3 models load, and unmaintained since 2026-01-12. Commits, not releases, because it cuts none.",
    },
    {
        "name": "Anthropic status",
        "type": "rss",
        "url": "https://status.anthropic.com/history.atom",
        "limit": 10,
        "notes": "Incidents and postmortems on the metered API our raters and day-file run on.",
    },

    # ── Tier 2: Hugging Face — where models actually ship ────────────────────
    # ⭐ GitHub is the wrong place to watch models. Measured 2026-08-30:
    # Wan2.2's last commit was March, Hunyuan3D-2's October, and Wan /
    # Hunyuan3D / ACE-Step / TRELLIS / ComfyUI-GGUF cut NO GitHub releases at
    # all. The HF API returns licence, gated status and parameter counts in one
    # keyless call — the three things that decide if a model is usable to us.
    # ⚠️ Author matching is CASE-SENSITIVE: `ace-step` returns zero, `ACE-Step`
    # is the org. A zero-model org is a name error, and the fetcher says so.
    {"name": "HF — Qwen", "type": "hf_org", "url": "Qwen", "limit": 8,
     "notes": "Publisher of the qwen3.6 family we run as bosun-brain, and of Qwen2.5-VL on brownie."},
    {"name": "HF — Lightricks", "type": "hf_org", "url": "Lightricks", "limit": 8,
     "notes": "Publisher of LTX-Video. We run LTX-2.3."},
    {"name": "HF — Wan-AI", "type": "hf_org", "url": "Wan-AI", "limit": 8,
     "notes": "Publisher of Wan 2.2, our main video suite on brownie."},
    {"name": "HF — tencent", "type": "hf_org", "url": "tencent", "limit": 8,
     "notes": "Publisher of Hunyuan3D. We run 2.0, whose licence is still unresolved."},
    {"name": "HF — ACE-Step", "type": "hf_org", "url": "ACE-Step", "limit": 6,
     "notes": "Publisher of ACE-Step 1.5, our audio model."},
    {"name": "HF — black-forest-labs", "type": "hf_org", "url": "black-forest-labs", "limit": 6,
     "notes": "FLUX. We do not run it — the licence is the reason. Watch for that changing."},
    {"name": "HF — stabilityai", "type": "hf_org", "url": "stabilityai", "limit": 6,
     "notes": "Publisher of SDXL, which we run on brownie."},
    {"name": "HF — Comfy-Org", "type": "hf_org", "url": "Comfy-Org", "limit": 8,
     "notes": "Repackages models into ComfyUI-ready files — the form we can actually load."},
    {"name": "HF — city96", "type": "hf_org", "url": "city96", "limit": 8,
     "notes": "Author of ComfyUI-GGUF; publishes the GGUF quants that decide whether a model fits 16GB."},
    {"name": "HF — microsoft", "type": "hf_org", "url": "microsoft", "limit": 6,
     "notes": "Publisher of TRELLIS and phi. High volume, mixed relevance."},

    # Tier 2b: the quantisers — "here is the VRAM you actually need"
    {"name": "HF — bartowski (quants)", "type": "hf_org", "url": "bartowski", "limit": 10,
     "notes": "Ships GGUFs within days of a model's release. The fastest answer to whether something fits brownie's 16GB."},
    {"name": "HF — unsloth (quants)", "type": "hf_org", "url": "unsloth", "limit": 10,
     "notes": "Ships GGUFs and dynamic quants fast. ⚠️ Their own blog is 403 Cloudflare — the API is the way in."},
    # ⚠️ `mradermacher` deliberately EXCLUDED: very high volume, largely
    # uncensored merges, low signal-to-noise. Add only with hard filtering.

    # ── Tier 3: practitioner analysis ────────────────────────────────────────
    {
        "name": "Simon Willison's Blog",
        "type": "rss",
        "url": "https://simonwillison.net/atom/everything/",
        "limit": 20,
        "notes": "Independent practitioner; our single best source historically (32% of the old feed).",
    },
    {
        "name": "Latent Space",
        "type": "rss",
        "url": "https://www.latent.space/feed",
        "limit": 10,
        "notes": "AI practitioner newsletter and podcast.",
    },
    {
        "name": "Nathan Lambert — Interconnects",
        "type": "rss",
        "url": "https://www.interconnects.ai/feed",
        "limit": 10,
        "notes": "ML researcher; open models, licensing and training.",
    },
    {
        "name": "Ahead of AI — Sebastian Raschka",
        "type": "rss",
        "url": "https://magazine.sebastianraschka.com/feed",
        "limit": 8,
        "notes": "Implementation-level analysis of open models and architectures.",
    },
    {
        "name": "Import AI — Jack Clark",
        "type": "rss",
        "url": "https://importai.substack.com/feed",
        "limit": 8,
        "notes": "Weekly research and policy roundup.",
    },
    {
        "name": "AI Maker",
        "type": "rss",
        "url": "https://aimaker.substack.com/feed",
        "limit": 8,
        "notes": "General AI newsletter. ⚠️ Healthy feed (863KB) that produced zero items under the old Claude-only prompt — its yield is an editorial question, not a plumbing one. On probation: if it yields nothing under the stack-driven filter either, cut it.",
    },

    # ── Tier 4: hardware — a total blind spot until now ──────────────────────
    # sm_120, VRAM and driver reality decide what brownie can run.
    {
        "name": "Phoronix",
        "type": "rss",
        "url": "https://www.phoronix.com/rss.php",
        "limit": 12,
        "notes": "Linux/GPU/driver and compute-stack news; CUDA and kernel-level breakage.",
    },
    {
        "name": "TechPowerUp",
        "type": "rss",
        "url": "https://www.techpowerup.com/rss/news",
        "limit": 12,
        "notes": "GPU news and specs. ⚠️ High volume (~170 items in feed) — capped hard.",
    },
    {
        "name": "ServeTheHome",
        "type": "rss",
        "url": "https://www.servethehome.com/feed/",
        "limit": 8,
        "notes": "Server and accelerator hardware, memory and interconnect.",
    },

    # ── Tier 5: frontier vendors and deprecations ────────────────────────────
    {
        "name": "Hugging Face blog",
        "type": "rss",
        "url": "https://huggingface.co/blog/feed.xml",
        "limit": 10,
        "notes": "Model releases, quantisation and inference technique.",
    },
    {
        "name": "OpenAI news",
        "type": "rss",
        "url": "https://openai.com/news/rss.xml",
        "limit": 8,
        "notes": "Frontier vendor; relevant when it moves the open-model or pricing landscape.",
    },
    {
        "name": "Google AI blog",
        "type": "rss",
        "url": "https://blog.google/technology/ai/rss/",
        "limit": 8,
        "notes": "Publisher of Gemma, which we run on brownie as LTX-2.3's text encoder.",
    },
    {
        "name": "Anthropic model deprecations",
        "type": "page_digest",
        "url": "https://docs.claude.com/en/docs/about-claude/model-deprecations",
        "notes": "The retirement schedule for the metered models our raters and day-file call. Emits an item only when the page actually changes.",
    },
    {
        "name": "OpenAI deprecations",
        "type": "page_digest",
        "url": "https://platform.openai.com/docs/deprecations",
        "notes": "Same, for OpenAI. Emits an item only when the page changes.",
    },

    # ── Tier 6: Anthropic's own announcements ────────────────────────────────
    # ⚠️ DELIBERATELY DEMOTED, on the human's own measured verdict: of 61 items
    # Em rated, 42 were blocks — and 37 of the 43 blocked URLs were Anthropic's
    # own pages. Kept, because we do run Claude Code and the metered API and a
    # deprecation there is real. The demotion is done by the FILTER (an item
    # affecting no stack entry cannot reach `act`), not by deletion.
    {
        "name": "Anthropic News",
        "type": "scrape",
        "url": "https://www.anthropic.com/news",
        "notes": "Official news: model launches, deprecations, pricing.",
    },
    {
        "name": "Anthropic Engineering",
        "type": "scrape",
        "url": "https://www.anthropic.com/engineering",
        "notes": "Technical writeups and agent-building practice.",
    },
    {
        "name": "Anthropic Research Blog",
        "type": "scrape",
        "url": "https://www.anthropic.com/research",
        "notes": "Research publications.",
    },
    {
        "name": "Claude Docs Changelog",
        "type": "scrape",
        "url": "https://docs.claude.com/en/release-notes/overview",
        "notes": "API and docs changelog — where deprecations land.",
    },
    {
        "name": "Claude Code Changelog",
        "type": "changelog_md",
        "url": "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md",
        "notes": "⚠️ Replaces the old 'Claude Code Docs' scrape, which yielded 0 items — NOT because redirects were unfollowed (the fetcher always followed them) but because that URL 301s to a GitHub blob page the link-scraper cannot read. The raw markdown is the real source.",
    },
    {
        "name": "Anthropic Release Notes",
        "type": "release_notes",
        "url": "https://support.claude.com/en/articles/12138966-release-notes",
        "notes": "Consumer-app release notes. ⚠️ The single most-blocked source in the ranker (17 of 43 blocks). On probation: kept so the new filter's demotion can be MEASURED rather than assumed. If it still floods, cut it — with evidence.",
    },
    {
        "name": "Anthropic Python SDK releases",
        "type": "rss",
        "url": "https://github.com/anthropics/anthropic-sdk-python/releases.atom",
        "limit": 8,
        "notes": "The SDK our metered callers import.",
    },

    # ── Hacker News ──────────────────────────────────────────────────────────
    # ⚠️ Algolia ANDs multiple terms. Measured 2026-08-30 over 24h:
    # `claude` = 23 stories, `anthropic` = 10, but `claude+anthropic` = 2 —
    # so the shipped query has been quietly fetching a tenth of what it could.
    # One term per source. Do not "improve" these by adding words.
    {
        "name": "Hacker News — claude",
        "type": "hn",
        "url": "https://hn.algolia.com/api/v1/search?query=claude&tags=story&hitsPerPage=10&numericFilters=created_at_i>{}",
        "notes": "HN stories mentioning Claude.",
    },
    {
        "name": "Hacker News — ollama",
        "type": "hn",
        "url": "https://hn.algolia.com/api/v1/search?query=ollama&tags=story&hitsPerPage=8&numericFilters=created_at_i>{}",
        "notes": "Local inference reality — part of the beat r/LocalLLaMA covered before it went 403.",
    },
    {
        "name": "Hacker News — llama.cpp",
        "type": "hn",
        "url": "https://hn.algolia.com/api/v1/search?query=llama.cpp&tags=story&hitsPerPage=8&numericFilters=created_at_i>{}",
        "notes": "The GGUF lineage under everything we quantise.",
    },
    {
        "name": "Hacker News — gguf",
        "type": "hn",
        "url": "https://hn.algolia.com/api/v1/search?query=gguf&tags=story&hitsPerPage=8&numericFilters=created_at_i>{}",
        "notes": "Quantisation and the VRAM question. Low volume, high signal.",
    },
]
