"""Connection to the database."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables from the .env file (if any)
load_dotenv()

# Database address. If DATABASE_URL is not set, a local SQLite file `sigecedu.db` is used.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sigecedu.db")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite needs this option because Flask uses several threads
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
