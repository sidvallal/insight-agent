import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "data" / "schema_docs.md"
OUTPUT_FILE = BASE_DIR / "data" / "schema_chunks.json"


TABLE_PATTERN = re.compile(
    r"##\s+\d+\.\s+.*?—\s+`([^`]+)`(.*?)(?=\n##\s+\d+\.|\Z)",
    re.DOTALL,
)


def chunk_schema():
    schema_text = SCHEMA_FILE.read_text(encoding="utf-8")

    matches = TABLE_PATTERN.findall(schema_text)

    chunks = []

    for table_name, content in matches:
        content = content.strip()

        chunks.append(
            {
                "table": table_name,
                "content": content,
            }
        )

    OUTPUT_FILE.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Created {len(chunks)} schema chunks.")
    print(f"Saved to: {OUTPUT_FILE}")

    for chunk in chunks:
        print(f"- {chunk['table']}")


if __name__ == "__main__":
    chunk_schema()