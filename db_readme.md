# Local SQLite

Orders and P&L are stored in a local SQLite file. The path comes from `DB_PATH` in the env file (`src/env/sandbox.env` or `src/env/prod.env`); `src/helper_func/config.py` resolves it to `DB_PATH_FULL` under `src/`.

Typical value:

```
DB_PATH=db/data/trader_database.db
```

That file is created under `src/db/data/`. The `.db` file and SQLite WAL sidecars (`*.db-wal`, `*.db-shm`) are gitignored.

Helpers live in `[src/db/helper/db_connector.py](src/db/helper/db_connector.py)`. Importing them loads config, so `**--env=demo` or `--env=prod` is required**, and you must run from `src/` (same as `main.py`).

## Files


| File                                                                 | Function                                                                                          |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `[src/db/helper/db_connector.py](src/db/helper/db_connector.py)`     | `get_connection()`, `db_session()`, `ping_db()`. File path from `DB_PATH`.                        |
| `src/db/data/trader_database.db`                                     | Local database file (created on first connect, not committed).                                    |
| `[src/helper_func/config.py](src/helper_func/config.py)`             | Exposes `DB_PATH_FULL` from `DB_PATH`.                                                            |
| `[src/bootstrap/pre_load_check.py](src/bootstrap/pre_load_check.py)` | Treats `DB_PATH` as a mandatory env variable.                                                     |
| `alembic.ini` / `alembic/`                                           | Created by `alembic init` (not in the repo until you run setup). Progressive SQLModel migrations. |


## Check the connection

```bash
cd src
uv run python -c "from db.helper.db_connector import ping_db; ping_db()" --env=demo
```

`ping_db()` opens a session, runs `SELECT 1`, prints the file path on success, and returns `True` / `False`.

If you previously created `db/data/trader_database.db` as a **directory** (an empty folder with that name), SQLite cannot open it. Remove the folder, then ping again so the connector can create a real database file.

## Open a connection

Use `get_connection()` when you need to keep the connection across several steps (and close it yourself):

```python
from db.helper.db_connector import get_connection

conn = get_connection()
try:
    conn.execute("SELECT 1")
finally:
    conn.close()
```

The connection uses `sqlite3.Row` (access columns by name), `PRAGMA foreign_keys = ON`, and WAL journal mode. Parent directories of `DB_PATH` are created if they are missing.

## Insert and update (preferred: `db_session`)

`db_session()` opens a connection, **commits** if the block succeeds, **rolls back** if it raises, then **closes** the connection. Always pass values with `?` placeholders.

```python
from db.helper.db_connector import db_session

with db_session() as conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            instrument_token TEXT NOT NULL,
            net_pnl REAL
        )
        """
    )
    conn.execute(
        "INSERT INTO trades (status, instrument_token, net_pnl) VALUES (?, ?, ?)",
        ("open", "NSE_FO|61703", None),
    )
    trade_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "UPDATE trades SET status = ?, net_pnl = ? WHERE id = ?",
        ("closed", 1250.50, trade_id),
    )
```

Read rows the same way:

```python
with db_session() as conn:
    row = conn.execute(
        "SELECT id, status, net_pnl FROM trades WHERE id = ?",
        (trade_id,),
    ).fetchone()
    print(row["status"], row["net_pnl"])
```

Pass an explicit path only if you need a file other than `DB_PATH`:

```python
from pathlib import Path
from db.helper.db_connector import get_connection

conn = get_connection(Path("/tmp/scratch.db"))
```

Inspect the file in a shell:

```bash
sqlite3 src/db/data/trader_database.db
```

```sql
.tables
SELECT * FROM trades;
.quit
```

## Using SQLModel

The helpers above are raw `sqlite3`. For model-based insert/update/select, use [SQLModel](https://sqlmodel.tiangolo.com/). It sits on SQLAlchemy and uses **Pydantic** models as tables, which matches `OrderModel` in `src/DTO/order_model.py`.

Keep `OrderModel` / `ModifyOrderModel` for the Upstox HTTP API. Add separate `table=True` models for the journal (`Trade`, `Order`, `OrderChange`). API fields are not the same as persisted fields.

SQLModel is not in `pyproject.toml` yet:

```bash
uv add sqlmodel
```

Point the engine at the same file as `DB_PATH` (`DB_PATH_FULL` from config). Run from `src/` with `--env=demo` or `--env=prod`, same as `get_connection()`.

```python
from sqlmodel import Field, Session, SQLModel, create_engine, select

from helper_func.config import DB_PATH_FULL

class Trade(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: str
    instrument_token: str
    net_pnl: float | None = None

engine = create_engine(
    f"sqlite:///{DB_PATH_FULL}",
    connect_args={"check_same_thread": False},
)
SQLModel.metadata.create_all(engine)  # creates missing tables only; see Alembic below

with Session(engine) as session:
    trade = Trade(status="open", instrument_token="NSE_FO|61703")
    session.add(trade)
    session.commit()
    session.refresh(trade)

    trade.status = "closed"
    trade.net_pnl = 1250.50
    session.add(trade)
    session.commit()

    row = session.exec(select(Trade).where(Trade.id == trade.id)).one()
    print(row.status, row.net_pnl)
```

`Session(engine)` is the SQLModel equivalent of `db_session()`: commit on success, then close. Do not mix a `sqlite3` connection from `get_connection()` with a SQLModel `Session` on the same write.

To keep the same SQLite settings as `db_connector.py` (foreign keys and WAL):

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()
```

Create parent directories of `DB_PATH_FULL` before `create_engine` if they do not exist (`DB_PATH_FULL.parent.mkdir(parents=True, exist_ok=True)`). The directory-vs-file check in `get_connection()` still applies: if `trader_database.db` is a folder, remove it first.

`create_all()` does **not** alter tables that already exist (new columns, types, indexes). For that, use Alembic.

## Progressive migrations with Alembic

[Alembic](https://alembic.sqlalchemy.org/) is the migration helper for SQLModel (same metadata as SQLAlchemy). Changing a `SQLModel` class never updates the SQLite file by itself. Alembic writes numbered revision scripts and applies them in order.

Neither `sqlmodel` nor `alembic` is in `pyproject.toml` yet:

```bash
uv add sqlmodel alembic
```

### One-time setup

From the **repo root** so `uv run alembic` works without `cd src`:

```bash
uv run alembic init alembic
```

That creates `alembic.ini` and `alembic/`. Set `sqlalchemy.url` later in code, not as a checked-in password. In `alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = src
```

`prepend_sys_path = src` lets revision/`env.py` import `helper_func` and `db` the same way `main.py` does.

**Do not import `helper_func.config` from Alembic.** That module always parses `--env` and will fail (`alembic upgrade` has no `--env`). Load the env file and build the SQLite URL yourself in `alembic/env.py`:

```python
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Import every table=True model so they register on SQLModel.metadata
# from db.models import Trade, Order, OrderChange

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

src_root = Path(__file__).resolve().parents[1] / "src"
env_name = os.environ.get("UPSTOX_ALEMBIC_ENV", "demo")  # demo -> sandbox.env, prod -> prod.env
env_file = "prod.env" if env_name == "prod" else "sandbox.env"
load_dotenv(src_root / "env" / env_file, override=True)

db_rel = (os.getenv("DB_PATH") or "").strip().strip('"').strip("'")
db_path = (src_root / db_rel).resolve()
db_path.parent.mkdir(parents=True, exist_ok=True)
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite-friendly ALTER TABLE
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

`render_as_batch=True` is required for many SQLite alters (add/drop column by recreating the table).

### Each schema change

1. Edit the SQLModel class (`table=True`).
2. Import that class from `alembic/env.py` so autogenerate can see it.
3. Generate a revision (from repo root):

```bash
UPSTOX_ALEMBIC_ENV=demo uv run alembic revision --autogenerate -m "add net_pnl to trades"
```

1. **Open the new file under `alembic/versions/`.** Autogenerate misses renames, some type tweaks, and data backfills. Fix `upgrade()` / `downgrade()` by hand if needed.
2. Apply all unapplied revisions:

```bash
UPSTOX_ALEMBIC_ENV=demo uv run alembic upgrade head
```

Useful commands:

```bash
UPSTOX_ALEMBIC_ENV=demo uv run alembic current
UPSTOX_ALEMBIC_ENV=demo uv run alembic history
UPSTOX_ALEMBIC_ENV=demo uv run alembic downgrade -1
```

Use `UPSTOX_ALEMBIC_ENV=prod` against `src/env/prod.env` (and that env’s `DB_PATH`). Do not point demo and prod at the same `.db` file.

Alembic records applied revisions in an `alembic_version` table in the same SQLite file.

### Rules for this project


| Do                                                              | Do not                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Own schema with Alembic after the first real table              | Rely on `SQLModel.metadata.create_all()` to add columns                      |
| Keep using `db_session()` / SQLModel `Session` for **data**     | Mix `CREATE TABLE IF NOT EXISTS` in app code with Alembic on the same tables |
| Review every autogenerated revision                             | Delete `trader_database.db` on prod to “fix” schema                          |
| Wipe the demo `.db` only while the schema is still experimental | Import `helper_func.config` from `alembic/env.py`                            |


While you are still iterating in demo, deleting `src/db/data/trader_database.db` and running `create_all()` is fine. Once you care about existing trades, use Alembic only.