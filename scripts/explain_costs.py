"""Show the planner cost of every benchmark query, to choose APPROVAL_COST_THRESHOLD.

    python -m scripts.explain_costs
"""

import json

from src import config, db

questions = json.loads(config.QUESTIONS_FILE.read_text(encoding="utf-8"))
costs = sorted(
    (cost, item["id"])
    for item in questions
    if (cost := db.estimate_cost(item["gold_sql"])) is not None
)

print("Most expensive benchmark queries:")
for cost, qid in costs[-8:]:
    print(f"  {qid:6} {cost:>12,.0f}")

print(f"\nmedian {costs[len(costs) // 2][0]:,.0f} | max {costs[-1][0]:,.0f}")
print(f"current threshold: {config.APPROVAL_COST_THRESHOLD:,.0f}")
print("Set APPROVAL_COST_THRESHOLD in .env to a bit above the max, so normal questions never ask.")