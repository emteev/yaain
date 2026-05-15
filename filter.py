"""
filter.py — Claude-powered relevance filter.

For each candidate item:
  1. If it has an extracted summary (from RSS), use that + ask Claude for include/why only
  2. If no summary, ask Claude for include/summary/why

Returns only items that pass, each augmented with:
  summary    : str   (extracted from source or Claude-generated)
  why        : str   (Claude-generated)
  author     : str   (preserved from source)
  image      : str   (preserved from source)
"""

import json
import anthropic

SYSTEM_PROMPT_WITH_SUMMARY = """You are a strict content filter for a professional RSS feed.

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
  "why": "1 sentence. What this means for someone using Claude tools professionally."
}

If include is false, why should be an empty string.
Return ONLY the JSON object. No preamble, no explanation."""

SYSTEM_PROMPT_NO_SUMMARY = """You are a strict content filter for a professional RSS feed.

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


def filter_items(items: list[dict], api_key: str) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)
    passed = []

    for item in items:
        title = item.get("title", "").strip()
        body = item.get("body", "").strip()
        source = item.get("source_name", "")
        notes = item.get("_source_notes", "")
        extracted_summary = item.get("summary", "").strip()

        if not title:
            continue

        user_content = f"""Source: {source}
Source context: {notes}

Title: {title}

Body excerpt:
{body[:1500] if body else "(no body text available)"}"""

        # Choose prompt based on whether we have an extracted summary
        has_summary = bool(extracted_summary)
        system_prompt = SYSTEM_PROMPT_WITH_SUMMARY if has_summary else SYSTEM_PROMPT_NO_SUMMARY

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)

            if result.get("include"):
                # Use extracted summary if available, otherwise use Claude's
                if has_summary:
                    item["summary"] = extracted_summary
                else:
                    item["summary"] = result.get("summary", "")
                
                item["why"] = result.get("why", "")
                # Preserve author and image from source
                # Clean internal fields
                item.pop("_source_notes", None)
                item.pop("body", None)
                passed.append(item)
                print(f"    ✓ {title[:70]}")
            else:
                print(f"    ✗ {title[:70]}")

        except Exception as e:
            print(f"    [filter error] {title[:50]}: {e}")

    return passed
