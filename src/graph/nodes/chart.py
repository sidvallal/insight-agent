"""Chart node: build a chart from the shape of the result."""

from src.charts import suggest_chart
from src.graph.state import AgentState


def chart_node(state: AgentState) -> AgentState:
    if state.get("error") or not state.get("rows"):
        return {**state, "chart": None}
    chart = suggest_chart(state["columns"], state["rows"], title=state.get("user_question", ""))
    return {**state, "chart": chart}