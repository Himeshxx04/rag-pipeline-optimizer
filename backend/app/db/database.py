from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base



import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pande@localhost:5432/rag_pipeline_db"  # fallback for local dev
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"client_encoding": "utf8"}
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


