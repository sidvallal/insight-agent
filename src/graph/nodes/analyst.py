"""Analyst node: turn the SQL result into a plain-English answer."""

from src import config, llm
from src.graph.state import AgentState

PROMPT = """
You are a data analyst. Answer the question using ONLY the SQL result below.
Be concise. Do not invent information. {truncation_note}

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
    if len(rows) > len(shown):
        note = (
            f"Only the first {len(shown)} of {len(rows)} rows are shown; "
            "say so if it matters for the answer."
        )

    answer = llm.ask_llm(
        PROMPT.format(question=state["question"], result=result, truncation_note=note)
    )
    return {**state, "answer": answer}
