"""LLM access: one cached model plus token-usage tracking."""

import os
from functools import lru_cache

from src import config

# Running token totals; the evaluation script reads these to estimate cost.
usage = {"input": 0, "output": 0}


@lru_cache(maxsize=1)
def get_llm():
    """Create the Groq chat model once and reuse it."""
    from langchain_groq import ChatGroq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from the .env file.")

    return ChatGroq(model=config.LLM_MODEL, temperature=0, api_key=api_key)


def ask_llm(prompt: str) -> str:
    """Send a prompt to the LLM and return the text answer.

    Every node calls this single function, so tests only need to patch it.
    """
    response = get_llm().invoke(prompt)

    meta = getattr(response, "usage_metadata", None) or {}
    usage["input"] += meta.get("input_tokens", 0)
    usage["output"] += meta.get("output_tokens", 0)

    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return content.strip()


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate the USD cost from token counts."""
    return (
        input_tokens * config.PRICE_PER_M_INPUT
        + output_tokens * config.PRICE_PER_M_OUTPUT
    ) / 1_000_000


if __name__ == "__main__":
    print(ask_llm("Reply with exactly: Groq connection successful"))
