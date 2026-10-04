import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load database settings from .env
load_dotenv()

# Read database credentials
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Create database connection URL
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Test connection and print PostgreSQL version
with engine.connect() as connection:
    version = connection.execute(
        text("SELECT version()")
    ).scalar()

    print("Connected successfully!")
    print("PostgreSQL version:")
    print(version)