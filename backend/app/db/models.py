from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False)

    num_chunks = Column(Integer)
    num_embeddings = Column(Integer)

    # NEW FIELD
    similarity_threshold = Column(Float, nullable=False, default=0.15)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, nullable=False)

    question = Column(Text, nullable=False)
    top_k = Column(Integer, nullable=False)

    sources = Column(JSON, nullable=False)

    model_name = Column(String)

    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)

    latency_ms = Column(Float)
    cost_usd = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
