"""Load the Olist CSV files into PostgreSQL (tables come from db/schema.sql).

    python -m scripts.import_data           # load (fails if tables already have rows)
    python -m scripts.import_data --reset   # empty the tables first, then load
"""

import argparse

import pandas as pd
from sqlalchemy import text

from src import config
from src.db import get_admin_engine

CSV_FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="truncate tables before loading")
    args = parser.parse_args()

    engine = get_admin_engine()
    tables = [name.removesuffix(".csv") for name in CSV_FILES]

    with engine.begin() as connection:
        if args.reset:
            connection.execute(text(f"TRUNCATE {', '.join(tables)}"))
            print("Tables truncated.")
        else:
            for table in tables:
                count = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if count:
                    raise SystemExit(
                        f"{table} already has {count:,} rows. "
                        "Re-run with --reset to avoid duplicate data."
                    )

    for filename in CSV_FILES:
        table = filename.removesuffix(".csv")
        total = 0
        print(f"Importing {filename} ...")
        for chunk in pd.read_csv(config.DATA_DIR / filename, chunksize=5000):
            chunk.to_sql(table, con=engine, if_exists="append", index=False)
            total += len(chunk)
        print(f"  {total:,} rows -> {table}")

    print("Import completed.")


if __name__ == "__main__":
    main()
