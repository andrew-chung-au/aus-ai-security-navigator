from __future__ import annotations

from typing import Any

from llm_client import llm_text


def rewrite_query(user_query: str) -> tuple[str, Any | None]:
    if not user_query.strip():
        return user_query, None

    instructions = """You rewrite user questions into a single retrieval-friendly search query for an ACSC AI security guidance corpus.

Rules:
- Preserve the user's original meaning.
- Keep important audience constraints when present, including organisation size and AI role.
- Expand vague wording into likely ACSC-style terminology when helpful.
- Remove filler words and conversational phrasing.
- Fix obvious spelling issues.
- Do not invent facts.
- Do not answer the question.
- Return exactly one rewritten query as plain text.
"""

    user_prompt = f"Original query:\n{user_query}"

    try:
        rewritten, usage = llm_text(
            instructions=instructions,
            user_prompt=user_prompt,
        )
    except Exception:
        return user_query, None

    rewritten = rewritten.strip()
    if not rewritten:
        return user_query, usage

    return rewritten, usage