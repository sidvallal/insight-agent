
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "dataset_summary.csv"

summary = []

for file in sorted(DATA_DIR.glob("*.csv")):
    if file.name == OUTPUT_FILE.name:
        continue

    df = pd.read_csv(file)
    summary.append({
        "table_name": file.stem,
        "row_count": len(df),
        "column_count": len(df.columns)
    })

summary_df = pd.DataFrame(summary)
summary_df.to_csv(OUTPUT_FILE, index=False)

print(summary_df.to_string(index=False))
print(f"\nSummary saved to: {OUTPUT_FILE}")
