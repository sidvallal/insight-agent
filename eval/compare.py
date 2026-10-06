"""Result-set comparison used by the evaluation.

Two result sets match when they contain the same VALUES, ignoring:
  * column names / aliases (``total`` vs ``total_orders``)
  * row order
  * tiny float differences (numbers are rounded to 2 decimals)

Extra or missing columns still count as a mismatch.
"""

from datetime import date, datetime
from decimal import Decimal


def normalize_value(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), 2)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value) if not isinstance(value, str) else value


def normalize_rows(rows) -> list[tuple]:
    """Turn rows (lists, tuples or dicts) into sorted tuples of normalized values."""
    normalized = []
    for row in rows:
        values = row.values() if isinstance(row, dict) else row
        normalized.append(tuple(normalize_value(v) for v in values))
    return sorted(normalized, key=repr)


def results_match(generated_rows, gold_rows) -> bool:
    if generated_rows is None or gold_rows is None:
        return False
    return normalize_rows(generated_rows) == normalize_rows(gold_rows)
