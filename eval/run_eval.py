"""Evaluate the baseline Text-to-SQL system."""

import json
import sys
import time
from pathlib import Path

from sqlalchemy import text

# Allow importing baseline.py from the src directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from baseline import engine, generate_sql

QUESTIONS_FILE = PROJECT_ROOT / "eval" / "questions.json"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
OUTPUT_FILE = RESULTS_DIR / "baseline.json"


def execute_query(sql: str):
    """Execute SQL and return rows as normalized tuples."""
    with engine.connect() as connection:
        result = connection.execute(text(sql))
        rows = [tuple(row) for row in result.fetchall()]

    # Sorting makes comparison independent of row order.
    return sorted(rows, key=lambda row: repr(row))


def results_match(generated, expected) -> bool:
    """Compare result sets without considering row order."""
    return generated == expected


def evaluate_question(question_data: dict) -> dict:
    """Generate and evaluate SQL for one question."""
    question_id = question_data["id"]
    question = question_data["question"]
    gold_sql = question_data["gold_sql"]

    start_time = time.perf_counter()

    try:
        generated_sql = generate_sql(question)
        generation_time = time.perf_counter() - start_time

        generated_result = execute_query(generated_sql)
        gold_result = execute_query(gold_sql)

        passed = results_match(generated_result, gold_result)

        return {
            "id": question_id,
            "question": question,
            "generated_sql": generated_sql,
            "gold_sql": gold_sql,
            "passed": passed,
            "latency_seconds": round(generation_time, 3),
            "error": None,
        }

    except Exception as error:
        return {
            "id": question_id,
            "question": question,
            "generated_sql": None,
            "gold_sql": gold_sql,
            "passed": False,
            "latency_seconds": round(time.perf_counter() - start_time, 3),
            "error": str(error),
        }


def main():
    """Run the complete evaluation."""
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
        questions = json.load(file)

    results = []
    total = len(questions)

    for index, question_data in enumerate(questions, start=1):
        print(f"[{index}/{total}] Evaluating {question_data['id']}")

        result = evaluate_question(question_data)
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} | {result['latency_seconds']}s")

        if result["error"]:
            print(f"  Error: {result['error']}")

    passed = sum(result["passed"] for result in results)
    failed = total - passed

    latencies = [result["latency_seconds"] for result in results]
    average_latency = sum(latencies) / total if total else 0

    summary = {
        "total_questions": total,
        "passed": passed,
        "failed": failed,
        "accuracy": round(passed / total, 4) if total else 0,
        "average_latency_seconds": round(average_latency, 3),
        "estimated_cost_usd": None,
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print("\nEvaluation Summary")
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Accuracy: {summary['accuracy'] * 100:.2f}%")
    print(f"Average latency: {summary['average_latency_seconds']}s")
    print("Estimated cost: Not measured")
    print(f"Results saved to: {OUTPUT_FILE}")

    engine.dispose()


if __name__ == "__main__":
    main()