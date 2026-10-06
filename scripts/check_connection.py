"""Check the PostgreSQL connection.   python -m scripts.check_connection"""

from sqlalchemy import text

from src.db import get_engine

with get_engine().connect() as connection:
    print("Connected successfully!")
    print(connection.execute(text("SELECT version()")).scalar())
