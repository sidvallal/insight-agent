"""Small helpers shared by the baselines and the graph nodes."""

import re

_FENCE_START = re.compile(r"^```[a-zA-Z]*\s*\n?")
_FENCE_END = re.compile(r"\n?```\s*$")


def clean_sql(text: str) -> str:
    """Strip markdown code fences and whitespace from an LLM SQL answer."""
    text = text.strip()
    text = _FENCE_START.sub("", text)
    text = _FENCE_END.sub("", text)
    return text.strip()


def format_schema(chunks: list) -> str:
    """Format retrieved schema chunks for a prompt.

    The table name MUST be included: the chunk text itself does not contain it.
    """
    parts = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            parts.append(f"TABLE: {chunk['table']}\n{chunk['content']}")
        else:
            parts.append(str(chunk))
    return "\n\n".join(parts)


def format_examples(examples: list) -> str:
    """Format retrieved few-shot examples as 'QUESTION / SQL' blocks."""
    parts = []
    for example in examples:
        if isinstance(example, dict):
            sql = example["content"].split("SQL:", 1)[-1].strip()
            parts.append(f"QUESTION: {example['question']}\nSQL:\n{sql}")
        else:
            parts.append(str(example))
    return "\n\n".join(parts)
