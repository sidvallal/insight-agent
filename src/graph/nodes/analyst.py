"""Analyst node: turn the SQL result into a plain-English answer."""

from src import config, llm
from src.graph.state import AgentState

PROMPT = """
You are a data analyst. Answer the question using ONLY the SQL result below.
Be concise: 2 to 4 sentences with the key numbers. The user already sees the full
result table, so do not repeat it. Do not invent information. {truncation_note}

Question:
{question}

SQL result:
{result}

Give the final answer in plain English.
"""


def analyst_node(state: AgentState) -> AgentState:
    error = state.get("error", "")
    if error:
        return {**state, "answer": f"The SQL query could not be executed: {error}"}

    columns = state.get("columns", [])
    rows = state.get("rows", [])

    if not rows:
        return {**state, "answer": "The query returned no data for this question."}

    shown = rows[: config.MAX_ROWS_TO_LLM]
    result = [dict(zip(columns, row)) for row in shown]

    note = ""
    total = state.get("row_count", len(rows))
    if total > len(shown):
        note = (
            f"Only the first {len(shown)} of {total} rows are shown; "
            "say so if it matters for the answer."
        )
    if state.get("truncated"):
        note += (
            f" The query result was cut off at {config.MAX_ROWS:,} rows, "
            "so the real total is larger; say so."
        )

    answer = llm.ask_llm(
        PROMPT.format(question=state["question"], result=result, truncation_note=note)
    )
    return {**state, "answer": answer}