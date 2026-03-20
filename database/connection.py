import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', '')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'processos')}"
)

_schema = os.getenv("POSTGRES_SCHEMA", "")
_connect_args = {"options": f"-c search_path={_schema},public"} if _schema else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Retorna uma nova sessão. O chamador é responsável por fechar."""
    return SessionLocal()


@contextmanager
def db_session():
    """Context manager com commit/rollback automático."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Cria todas as tabelas no banco."""
    from models import Base  # noqa: F401 – importa todos os models via __init__
    Base.metadata.create_all(bind=engine)
    print("Banco de dados inicializado com sucesso.")
