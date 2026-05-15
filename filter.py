"""
filter.py — Claude-powered topic gate.

For each candidate item, asks Claude one question: is this specifically about
the Claude family of products? Editorial quality (depth, novelty, hype) is
judged downstream by the human ranker (rank.html), so this filter deliberately
does not gatekeep on those dimensions.

For each passing item:
  summary    : str   (extracted from source if present, else Claude-generated)
  why        : str   (Claude-generated, 1 sentence)
"""

import json
import anthropic

SYSTEM_PROMPT_WITH_SUMMARY = """You are a topic gate for an RSS feed about Anthropic's Claude products.

INCLUDE the item if it is specifically about any of:
- Claude models (claude.ai, the API, the mobile app)
- Claude Code (the CLI / agentic coding tool)
- Cowork (Anthropic's desktop automation tool)
- The Anthropic API, SDKs, or developer platform
- Anthropic research, papers, or company news
- A direct, useful comparison between Claude and another model

EXCLUDE only:
- General AI / industry news that does not mention Claude or Anthropic
- Posts about other models (GPT, Gemini, Llama, etc.) with no Claude angle

Do NOT exclude for being "basic", "opinion", "community discussion", "how-to",
or "not substantive enough". A human will rate everything that passes; this
gate's only job is on-topic vs off-topic.

Return a JSON object with this exact shape:
{
  "include": true | false,
  "why": "1 sentence. What this means for someone using Claude tools."
}

If include is false, why should be an empty string.
Return ONLY the JSON object."""

SYSTEM_PROMPT_NO_SUMMARY = """You are a topic gate for an RSS feed about Anthropic's Claude products.

INCLUDE the item if it is specifically about any of:
- Claude models (claude.ai, the API, the mobile app)
- Claude Code (the CLI / agentic coding tool)
- Cowork (Anthropic's desktop automation tool)
- The Anthropic API, SDKs, or developer platform
- Anthropic research, papers, or company news
- A direct, useful comparison between Claude and another model

EXCLUDE only:
- General AI / industry news that does not mention Claude or Anthropic
- Posts about other models (GPT, Gemini, Llama, etc.) with no Claude angle

Do NOT exclude for being "basic", "opinion", "community discussion", "how-to",
or "not substantive enough". A human will rate everything that passes; this
gate's only job is on-topic vs off-topic.

Return a JSON object with this exact shape:
{
  "include": true | false,
  "summary": "2 sentences. What happened or what was discovered. Factual, no filler.",
  "why": "1 sentence. What this means for someone using Claude tools."
}

If include is false, summary and why should be empty strings.
Return ONLY the JSON object."""


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

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)

            if result.get("include"):
                if has_summary:
                    item["summary"] = extracted_summary
                else:
                    item["summary"] = result.get("summary", "")

                item["why"] = result.get("why", "")
                item.pop("_source_notes", None)
                item.pop("body", None)
                passed.append(item)
                print(f"    ✓ {title[:70]}")
            else:
                print(f"    ✗ {title[:70]}")

        except Exception as e:
            print(f"    [filter error] {title[:50]}: {e}")

    return passed
