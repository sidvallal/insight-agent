"""Create the read-only PostgreSQL user used by the agent.

    python -m scripts.create_readonly_user

Needs DB_RO_USER and DB_RO_PASSWORD in .env (choose any name and password).
It connects with your admin account (DB_USER) to create the role, then the
agent connects as DB_RO_USER, which can only SELECT.
"""

import os

from sqlalchemy import text

from src.db import get_admin_engine


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def main():
    user = os.getenv("DB_RO_USER")
    password = os.getenv("DB_RO_PASSWORD")
    database = os.getenv("DB_NAME")
    if not user or not password:
        raise SystemExit("Set DB_RO_USER and DB_RO_PASSWORD in .env first.")

    role, db = quote_ident(user), quote_ident(database)

    with get_admin_engine().connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")

        exists = connection.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": user}
        ).scalar()
        verb = "ALTER" if exists else "CREATE"
        connection.execute(text(f"{verb} ROLE {role} LOGIN PASSWORD :password"), {"password": password})

        connection.execute(text(f"GRANT CONNECT ON DATABASE {db} TO {role}"))
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        connection.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}"))
        connection.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {role}"))
        connection.execute(text(f"ALTER ROLE {role} SET default_transaction_read_only = on"))
        connection.execute(text(f"ALTER ROLE {role} SET statement_timeout = '30s'"))

    print(f"Read-only user '{user}' is ready ({'updated' if exists else 'created'}).")


if __name__ == "__main__":
    main()