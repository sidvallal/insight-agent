"""Pick a chart from the SHAPE of a query result (no LLM involved).

Returns a Plotly figure as a plain dict, or None when a chart would not help:
    date-like first column + numbers  -> line chart
    text first column + numbers       -> bar chart (top 20 by the first number)
Render it with:  plotly.graph_objects.Figure(spec)
"""

import re

from src import config

_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?")
MAX_BARS = 20


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _numeric_columns(columns: list[str], rows: list[list], skip: int = 0) -> list[int]:
    result = []
    for index in range(skip, len(columns)):
        values = [row[index] for row in rows if row[index] is not None]
        if values and all(_is_number(v) for v in values):
            result.append(index)
    return result


def _is_date_column(rows: list[list], index: int) -> bool:
    values = [row[index] for row in rows if row[index] is not None]
    return bool(values) and all(isinstance(v, str) and _DATE.match(v) for v in values)


def _is_text_column(rows: list[list], index: int) -> bool:
    values = [row[index] for row in rows if row[index] is not None]
    return bool(values) and all(isinstance(v, str) for v in values)


def suggest_chart(columns: list[str], rows: list[list], title: str = "") -> dict | None:
    if len(rows) < 2 or len(columns) < 2:
        return None

    numeric = _numeric_columns(columns, rows, skip=1)
    if not numeric:
        return None

    layout = {
        "title": {"text": title[:90]},
        "xaxis": {"title": {"text": columns[0]}},
        "yaxis": {"title": {"text": columns[numeric[0]]}},
        "legend": {"title": {"text": ""}},
    }

    if _is_date_column(rows, 0):
        if len(rows) > config.CHART_MAX_POINTS:
            return None
        ordered = sorted(rows, key=lambda r: r[0] or "")
        traces = [
            {"type": "scatter", "mode": "lines+markers", "name": columns[i],
             "x": [r[0] for r in ordered], "y": [r[i] for r in ordered]}
            for i in numeric[:3]
        ]
        return {"data": traces, "layout": layout}

    if _is_text_column(rows, 0):
        first = numeric[0]
        ordered = sorted(rows, key=lambda r: (r[first] is None, -(r[first] or 0)))[:MAX_BARS]
        layout["xaxis"]["tickangle"] = -40
        return {
            "data": [{"type": "bar", "name": columns[first],
                      "x": [r[0] for r in ordered], "y": [r[first] for r in ordered]}],
            "layout": layout,
        }

    return None