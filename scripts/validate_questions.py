"""Run every gold SQL once to confirm it executes.   python -m scripts.validate_questions"""

import json

from src import config
from src.db import run_query

questions = json.loads(config.QUESTIONS_FILE.read_text(encoding="utf-8"))
failed = 0

for item in questions:
    try:
        _, rows = run_query(item["gold_sql"])
        print(f"PASS {item['id']}  ({len(rows)} rows)")
    except Exception as exc:
        failed += 1
        print(f"FAIL {item['id']}  {exc}")

print(f"\n{len(questions) - failed}/{len(questions)} gold queries run successfully.")
