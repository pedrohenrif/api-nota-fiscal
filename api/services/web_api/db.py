from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from services.web_api.config import POSTGRES_URL

Base = declarative_base()
engine = create_engine(POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
