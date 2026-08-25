import sqlite3
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import Engine
from helper_func.config import DB_PATH_FULL
from helper_func.fancy_print import fancy_print
from sqlmodel import create_engine, Session

_engine = None

def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH_FULL

    if path.exists() and path.is_dir():
        raise IsADirectoryError(
            f"Expected a SQLite file at {path}, but found a directory. "
            "Remove that folder and reconnect so the database file can be created."
        )

    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def db_session(db_path: Path | None = None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping_db(db_path: Path | None = None) -> bool:
    try:
        with db_session(db_path) as conn:
            conn.execute("SELECT 1")
        fancy_print(str(db_path or DB_PATH_FULL), border_color="green", title="SQLite connected")
        return True
    except Exception as err:
        fancy_print(str(err), border_color="red", title="SQLite connection failed")
        return False


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{DB_PATH_FULL}",
            connect_args={"check_same_thread": False},
            echo = True,
        )
    return _engine

@contextmanager
def orm_session(engine=None):
    """SQLModel/SQLAlchemy ORM session — for use with model classes (e.g. ApiLog)."""
    engine = engine or get_engine()
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()