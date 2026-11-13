"""Database setup. Uses PostgreSQL when DATABASE_URL is set (Render), SQLite otherwise."""
import os
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

url = os.environ.get("DATABASE_URL", "sqlite:///./dyslexia.db")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg2://", 1)
engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
                       pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(30), default="teacher")          # teacher, parent, clinician
    created_at = Column(DateTime, default=datetime.utcnow)
    children = relationship("Child", back_populates="owner", cascade="all, delete-orphan")


class Child(Base):
    __tablename__ = "children"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String(120), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), default="female")         # female / male
    native_speaker = Column(Boolean, default=True)        # tested in first language
    other_language = Column(Boolean, default=False)       # speaks another language
    school = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="children")
    assessments = relationship("Assessment", back_populates="child", cascade="all, delete-orphan",
                               order_by="Assessment.created_at")


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), index=True)
    module = Column(String(20), nullable=False)           # game, handwriting, eye
    risk = Column(Float)                                  # calibrated probability for this module
    label = Column(String(40))
    payload = Column(Text)                                # JSON: inputs and full model output
    created_at = Column(DateTime, default=datetime.utcnow)
    child = relationship("Child", back_populates="assessments")


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
