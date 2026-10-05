"""Evaluate the RAG-enhanced Text-to-SQL baseline."""

import json
import os
import sys
import time
from datetime import date, datetime, time as datetime_time
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_FILE = BASE_DIR / "eval" / "questions.json"
RESULTS_DIR = BASE_DIR / "eval" / "results"
RESULTS_FILE = RESULTS_DIR / "v2.json"

SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------
# Import RAG baseline
# ---------------------------------------------------------

from baseline_v2 import generate_sql


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_database_url():
    """Build PostgreSQL database URL from environment variables."""

    return (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
        f"/{os.getenv('DB_NAME')}"
    )


engine = create_engine(get_database_url())


# ---------------------------------------------------------
# JSON-safe value conversion
# ---------------------------------------------------------

def make_json_serializable(value):
    """
    Convert PostgreSQL/Python values into JSON-serializable values.
    """

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(
        value,
        (
            datetime,
            date,
            datetime_time,
        ),
    ):
        return value.isoformat()

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return str(value)


# ---------------------------------------------------------
# SQL execution
# ---------------------------------------------------------

def execute_sql(sql: str):
    """
    Execute SQL and return JSON-serializable rows.
    """

    with engine.connect() as connection:
        result = connection.execute(text(sql))

        rows = []

        for row in result:
            converted_row = tuple(
                make_json_serializable(value)
                for value in row
            )

            rows.append(converted_row)

    return rows


# ---------------------------------------------------------
# Result normalization
# ---------------------------------------------------------

def normalize_rows(rows):
    """
    Normalize result rows for comparison.

    Sorting makes the comparison independent of row order.
    """

    return sorted(
        rows,
        key=lambda row: repr(row),
    )


def results_match(generated_rows, gold_rows):
    """Compare generated and gold result sets."""

    return normalize_rows(
        generated_rows
    ) == normalize_rows(
        gold_rows
    )


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

def main():

    # -----------------------------------------------------
    # Load questions
    # -----------------------------------------------------

    with open(
        QUESTIONS_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        questions = json.load(f)

    # -----------------------------------------------------
    # Create results directory
    # -----------------------------------------------------

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Evaluation variables
    # -----------------------------------------------------

    detailed_results = []

    passed = 0
    failed = 0
    total_latency = 0.0

    # -----------------------------------------------------
    # Start evaluation
    # -----------------------------------------------------

    print("=" * 70)
    print("RAG TEXT-TO-SQL EVALUATION")
    print("=" * 70)

    for index, question_data in enumerate(
        questions,
        start=1,
    ):

        question_id = question_data["id"]
        question = question_data["question"]
        gold_sql = question_data["gold_sql"]

        print(
            f"\n[{index}/{len(questions)}] "
            f"{question_id}: {question}"
        )

        start_time = time.perf_counter()

        generated_sql = None
        generated_rows = None
        gold_rows = None
        error = None

        try:

            # -------------------------------------------------
            # Generate SQL using RAG baseline
            # -------------------------------------------------

            generated_sql = generate_sql(
                question
            )

            # -------------------------------------------------
            # Execute generated SQL
            # -------------------------------------------------

            generated_rows = execute_sql(
                generated_sql
            )

            # -------------------------------------------------
            # Execute gold SQL
            # -------------------------------------------------

            gold_rows = execute_sql(
                gold_sql
            )

            # -------------------------------------------------
            # Compare results
            # -------------------------------------------------

            passed_question = results_match(
                generated_rows,
                gold_rows,
            )

        except Exception as exc:

            passed_question = False
            error = str(exc)

        # -----------------------------------------------------
        # Latency
        # -----------------------------------------------------

        latency = (
            time.perf_counter()
            - start_time
        )

        total_latency += latency

        # -----------------------------------------------------
        # Pass / fail
        # -----------------------------------------------------

        if passed_question:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(
            f"  {status} | "
            f"{latency:.3f}s"
        )

        # -----------------------------------------------------
        # Store detailed result
        # -----------------------------------------------------

        detailed_results.append(
            {
                "id": question_id,
                "question": question,
                "gold_sql": gold_sql,
                "generated_sql": generated_sql,
                "generated_result": generated_rows,
                "gold_result": gold_rows,
                "passed": passed_question,
                "latency_seconds": round(
                    latency,
                    3,
                ),
                "error": error,
            }
        )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    total_questions = len(questions)

    accuracy = (
        passed / total_questions
        if total_questions
        else 0
    )

    average_latency = (
        total_latency / total_questions
        if total_questions
        else 0
    )

    summary = {
        "total_questions": total_questions,
        "passed": passed,
        "failed": failed,
        "accuracy": round(
            accuracy,
            4,
        ),
        "average_latency_seconds": round(
            average_latency,
            3,
        ),
        "estimated_cost_usd": None,
        "average_cost_per_question_usd": None,
    }

    # ---------------------------------------------------------
    # Final output
    # ---------------------------------------------------------

    output = {
        "summary": summary,
        "results": detailed_results,
    }

    # ---------------------------------------------------------
    # Save results
    # ---------------------------------------------------------

    with open(
        RESULTS_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # Print summary
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)

    print(
        f"Total questions : "
        f"{total_questions}"
    )

    print(
        f"Passed          : "
        f"{passed}"
    )

    print(
        f"Failed          : "
        f"{failed}"
    )

    print(
        f"Accuracy        : "
        f"{accuracy:.2%}"
    )

    print(
        f"Average latency : "
        f"{average_latency:.3f}s"
    )

    print("\nResults saved to:")

    print(RESULTS_FILE)


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    main()