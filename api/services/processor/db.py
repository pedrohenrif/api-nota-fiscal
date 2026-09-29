from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from services.common.postgres_url import normalize_postgres_url
from services.processor.config import POSTGRES_URL

Base = declarative_base()
engine = create_engine(normalize_postgres_url(POSTGRES_URL), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
