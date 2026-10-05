import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_FILE = BASE_DIR / "eval" / "questions.json"
OUTPUT_FILE = BASE_DIR / "data" / "few_shot_examples.json"


def main():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    easy = [q for q in questions if q["id"].startswith("E")]
    medium = [q for q in questions if q["id"].startswith("M")]
    hard = [q for q in questions if q["id"].startswith("H")]

    selected = (
        easy[:7]
        + medium[:8]
        + hard[:5]
    )

    examples = []

    for q in selected:
        examples.append(
            {
                "id": q["id"],
                "question": q["question"],
                "sql": q["gold_sql"],
            }
        )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            examples,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Created {len(examples)} few-shot examples.")
    print(f"Saved to: {OUTPUT_FILE}")

    for example in examples:
        print(f"- {example['id']}: {example['question']}")


if __name__ == "__main__":
    main()