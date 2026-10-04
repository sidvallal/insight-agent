import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME')}"
)
QUESTIONS_FILE = Path(__file__).resolve().parent.parent / "eval" / "questions.json"

engine = create_engine(DATABASE_URL)

with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
    questions = json.load(file)

passed = 0
failed = 0

for question in questions:
    question_id = question["id"]
    sql = question["gold_sql"]

    try:
        with engine.connect() as connection:
            connection.execute(text(sql))
        print(f"PASS: {question_id}")
        passed += 1
    except Exception as error:
        print(f"FAIL: {question_id} - {error}")
        failed += 1

print("\nValidation Summary")
print(f"Total: {len(questions)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")

engine.dispose()