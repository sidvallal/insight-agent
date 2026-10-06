"""Evaluate a pipeline version against eval/questions.json.

Usage (from the project root):
    python -m eval.run_eval --version baseline
    python -m eval.run_eval --version v2
    python -m eval.run_eval --version v3
    python -m eval.run_eval --version v3 --ids E001,M002     # quick check
    python -m eval.run_eval --version v3 --limit 10

Versions:
    baseline  full schema in the prompt
    v2        schema retrieval + few-shot examples
    v3        LangGraph workflow (router, retry loop, analyst)

Leakage guard: the few-shot store was built from these same questions, so for
each test question its own example id is excluded from retrieval.
"""

import argparse
import json
import time

from src import config, db, llm
from eval.compare import results_match

PREVIEW_ROWS = 5


def build_runner(version: str):
    """Return run(question, qid) -> dict(sql, columns, rows, error, retries, route)."""
    if version in ("baseline", "v2"):
        if version == "baseline":
            from src.pipelines.baseline_v1 import generate_sql
        else:
            from src.pipelines.baseline_v2 import generate_sql

        def run(question: str, qid: str) -> dict:
            sql = generate_sql(question, exclude_ids=[qid])
            try:
                columns, rows = db.run_query(sql)
                error = ""
            except Exception as exc:
                columns, rows, error = [], None, str(exc)
            return {"sql": sql, "columns": columns, "rows": rows,
                    "error": error, "retries": 0, "route": None}

        return run

    if version == "v3":
        from src.graph.builder import build_graph

        graph = build_graph()

        def run(question: str, qid: str) -> dict:
            state = graph.invoke(
                {"question": question, "retries": 0, "exclude_example_ids": [qid]}
            )
            error = state.get("error", "")
            return {"sql": state.get("sql", ""), "columns": state.get("columns", []),
                    "rows": None if error else state.get("rows"),
                    "error": error, "retries": state.get("retries", 0),
                    "route": state.get("route")}

        return run

    raise ValueError(f"Unknown version: {version}")


def summarize(results: list[dict], version: str) -> dict:
    total = len(results)
    passed = sum(r["passed"] for r in results)

    by_difficulty = {}
    for level in ("easy", "medium", "hard"):
        subset = [r for r in results if r["difficulty"] == level]
        if subset:
            ok = sum(r["passed"] for r in subset)
            by_difficulty[level] = {"passed": ok, "total": len(subset),
                                    "accuracy": round(ok / len(subset), 4)}

    tokens_in = sum(r["tokens_in"] for r in results)
    tokens_out = sum(r["tokens_out"] for r in results)
    cost = llm.estimate_cost(tokens_in, tokens_out)

    return {
        "version": version,
        "total_questions": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0,
        "by_difficulty": by_difficulty,
        "average_latency_seconds": round(sum(r["latency_seconds"] for r in results) / total, 3) if total else 0,
        "average_retries": round(sum(r["retries"] for r in results) / total, 3) if total else 0,
        "execution_errors": sum(1 for r in results if r["error"]),
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "estimated_cost_usd": round(cost, 4),
        "average_cost_per_question_usd": round(cost / total, 5) if total else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, choices=["baseline", "v2", "v3"])
    parser.add_argument("--ids", help="comma-separated question ids")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    questions = json.loads(config.QUESTIONS_FILE.read_text(encoding="utf-8"))
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in wanted]
    if args.limit:
        questions = questions[: args.limit]

    run = build_runner(args.version)
    results = []

    for number, item in enumerate(questions, start=1):
        print(f"[{number}/{len(questions)}] {item['id']}: {item['question']}")

        before_in, before_out = llm.usage["input"], llm.usage["output"]
        start = time.perf_counter()
        error, out = "", {}

        try:
            out = run(item["question"], item["id"])
            error = out["error"]
            _, gold_rows = db.run_query(item["gold_sql"])
            passed = (not error) and results_match(out["rows"], gold_rows)
        except Exception as exc:  # LLM / retrieval / unexpected failure
            passed, error, gold_rows = False, str(exc), None

        latency = time.perf_counter() - start
        rows = out.get("rows")

        results.append({
            "id": item["id"],
            "difficulty": item.get("difficulty"),
            "question": item["question"],
            "passed": bool(passed),
            "route": out.get("route"),
            "retries": out.get("retries", 0),
            "generated_sql": out.get("sql"),
            "gold_sql": item["gold_sql"],
            "generated_row_count": len(rows) if rows is not None else None,
            "gold_row_count": len(gold_rows) if gold_rows is not None else None,
            "generated_preview": rows[:PREVIEW_ROWS] if rows else rows,
            "gold_preview": gold_rows[:PREVIEW_ROWS] if gold_rows else gold_rows,
            "error": error,
            "latency_seconds": round(latency, 3),
            "tokens_in": llm.usage["input"] - before_in,
            "tokens_out": llm.usage["output"] - before_out,
        })
        print(f"   {'PASS' if passed else 'FAIL'}  {latency:.1f}s  retries={out.get('retries', 0)}")

    summary = summarize(results, args.version)

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = config.RESULTS_DIR / f"{args.version}.json"
    output_file.write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print(f"{args.version}: {summary['passed']}/{summary['total_questions']} "
          f"= {summary['accuracy']:.0%}")
    for level, stats in summary["by_difficulty"].items():
        print(f"  {level:7} {stats['passed']}/{stats['total']}")
    print(f"avg latency {summary['average_latency_seconds']}s | "
          f"est. cost ${summary['estimated_cost_usd']}")
    print(f"saved to {output_file}")


if __name__ == "__main__":
    main()
