
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(DATABASE_URL)

# Only the original Olist CSV files are included.
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

for filename in CSV_FILES:
    file_path = DATA_DIR / filename
    table_name = file_path.stem

    print(f"\nImporting {filename}...")

    total_rows = 0

    # for chunk in pd.read_csv(file_path, chunksize=10000):
    #     chunk.to_sql(
    #         name=table_name,
    #         con=engine,
    #         if_exists="append",
    #         index=False,
    #         method="multi",
    #         chunksize=1000,
    #     )
    
    for chunk in pd.read_csv(file_path, chunksize=5000):
        chunk.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            method=None,
        )
        total_rows += len(chunk)

    print(f"Imported {total_rows:,} rows into {table_name}")

engine.dispose()
print("\nImport completed!")
