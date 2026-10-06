"""Print the failed questions of a results file (for the failure log).

    python -m eval.show_failures v3
"""

import json
import sys

from src import config


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "v3"
    data = json.loads((config.RESULTS_DIR / f"{version}.json").read_text(encoding="utf-8"))

    failed = [r for r in data["results"] if not r["passed"]]
    print(f"{version}: {len(failed)} failed\n")

    for r in failed:
        print(f"{r['id']} ({r['difficulty']}) {r['question']}")
        if r["error"]:
            print(f"  error : {r['error'][:200]}")
        print(f"  rows  : generated={r['generated_row_count']} gold={r['gold_row_count']}")
        print(f"  gen   : {' '.join((r['generated_sql'] or '').split())[:250]}")
        print(f"  gold  : {' '.join(r['gold_sql'].split())[:250]}\n")


if __name__ == "__main__":
    main()
