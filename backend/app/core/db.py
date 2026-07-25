"""SQLAlchemy engine + session."""
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session
from .config import settings

engine = create_engine(
    settings.DATABASE_URL, pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE, max_overflow=settings.DB_MAX_OVERFLOW,
    connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Session  # type alias for typing


def commit_or_conflict(db: Session, msg: str = "Duplicate or invalid reference"):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, msg)


def delete_or_conflict(db: Session, row, msg: str = "Cannot delete — this record is still referenced by other data"):
    try:
        db.delete(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, msg)
