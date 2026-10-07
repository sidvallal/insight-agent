"""Rewrite a follow-up message into a standalone question."""

from src import llm
from src.graph.state import AgentState

PROMPT = """
Rewrite the user's follow-up message as ONE standalone question about the database.

- Use the conversation below to resolve words like "that", "it", "them", "those".
- Keep every filter and condition from the previous question that still applies.
- Return only the rewritten question, nothing else.

Conversation (most recent last):
{conversation}

Follow-up message:
{question}
"""


def rewrite_question_node(state: AgentState) -> AgentState:
    turns = state.get("history", [])[-3:]
    conversation = "\n".join(
        f"Question: {t['question']}\nSQL: {t['sql']}\nAnswer: {t['answer']}" for t in turns
    )
    standalone = llm.ask_llm(PROMPT.format(conversation=conversation, question=state["question"]))
    return {**state, "question": standalone.strip()}