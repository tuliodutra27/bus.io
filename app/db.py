import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """Dependency do FastAPI: abre e fecha a sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(max_tries: int = 30, delay: float = 2.0) -> None:
    """Aguarda o MySQL ficar disponível (o container do banco sobe junto)."""
    for attempt in range(1, max_tries + 1):
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return
        except OperationalError:
            print(f"[db] aguardando MySQL... ({attempt}/{max_tries})")
            time.sleep(delay)
    raise RuntimeError("Não foi possível conectar ao MySQL.")
