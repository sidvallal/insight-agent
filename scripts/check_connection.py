"""Check the PostgreSQL connections.   python -m scripts.check_connection"""

from sqlalchemy import text

from src.db import get_admin_engine, get_engine

for label, engine in (("admin", get_admin_engine()), ("agent", get_engine())):
    with engine.connect() as connection:
        user = connection.execute(text("SELECT current_user")).scalar()
        print(f"{label:6} connected as '{user}'")