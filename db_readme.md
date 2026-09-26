# Local SQLite

Orders and P&L are stored in a local SQLite file. The path comes from `DB_PATH` in the env file (`src/env/sandbox.env` or `src/env/prod.env`); `src/helper_func/config.py` resolves it to `DB_PATH_FULL` under `src/`.

Typical value:

```
DB_PATH=db/data/trades.db
```

That file is created under `src/db/data/`. The `.db` file and SQLite WAL sidecars (`*.db-wal`, `*.db-shm`) are gitignored.

Helpers live in `[src/db/helper/db_connector.py](src/db/helper/db_connector.py)`. Importing them loads config, so `**--env=demo` or `--env=prod` is required**, and you must run from `src/` (same as `main.py`).

## Files


| File                                                                 | Function                                                                                          |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `[src/db/helper/db_connector.py](src/db/helper/db_connector.py)`     | `get_connection()`, `db_session()`, `ping_db()`. File path from `DB_PATH`.                        |
| `[src/db/models/](src/db/models/)`                                   | SQLModel tables: `OrderDetail`, `Stock`, `ApiLog` (`order_details`, `stock_table`, `api_logs`). |
| `src/db/data/trades.db`                                              | Local database file (created on first connect / migration, not committed).                        |
| `[src/helper_func/config.py](src/helper_func/config.py)`             | Exposes `DB_PATH_FULL` from `DB_PATH`.                                                            |
| `[src/bootstrap/pre_load_check.py](src/bootstrap/pre_load_check.py)` | Treats `DB_PATH` as a mandatory env variable.                                                     |
| `[alembic.ini](alembic.ini)` / `[alembic/](alembic/)`                | Alembic config + revisions. `env.py` loads `DB_PATH` from sandbox/prod env.                       |
| `[src/planning/sqlmodel_alembic_setup.md](src/planning/sqlmodel_alembic_setup.md)` | Plan for models + Alembic setup.                                                    |


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
sqlite3 src/db/data/trades.db
```

```sql
.tables
SELECT * FROM order_details;
.quit
```

## Using SQLModel

The helpers above are raw `sqlite3`. For model-based insert/update/select, use [SQLModel](https://sqlmodel.tiangolo.com/). Persistence models live in `[src/db/models/](src/db/models/)`:

| Class | Table | Module |
| ----- | ----- | ------ |
| `OrderDetail` | `order_details` | `src/db/models/order_detail.py` |
| `Stock` | `stock_table` | `src/db/models/stock.py` |
| `ApiLog` | `api_logs` | `src/db/models/api_log.py` |

Keep `OrderModel` / `ModifyOrderModel` in `src/DTO/order_model.py` for the Upstox HTTP API. API fields are not the same as persisted fields.

Point the engine at the same file as `DB_PATH` (`DB_PATH_FULL` from config). Run from `src/` with `--env=demo` or `--env=prod`, same as `get_connection()`.

```python
from sqlmodel import Session, create_engine, select

from db.models import OrderDetail, Stock, ApiLog
from helper_func.config import DB_PATH_FULL

engine = create_engine(
    f"sqlite:///{DB_PATH_FULL}",
    connect_args={"check_same_thread": False},
)

with Session(engine) as session:
    row = session.exec(select(Stock).where(Stock.instrument_key == "NSE_EQ|INE848E01016")).first()
    print(row)
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

Create parent directories of `DB_PATH_FULL` before `create_engine` if they do not exist (`DB_PATH_FULL.parent.mkdir(parents=True, exist_ok=True)`). The directory-vs-file check in `get_connection()` still applies: if the DB path is a folder, remove it first.

Prefer Alembic for schema changes. Do not rely on `SQLModel.metadata.create_all()` once migrations are in use.

## Progressive migrations with Alembic

[Alembic](https://alembic.sqlalchemy.org/) is already initialized (`alembic.ini`, `alembic/`). `sqlmodel` and `alembic` are project dependencies. Changing a `SQLModel` class never updates the SQLite file by itself — generate and apply a revision.

### Config already in place

In `alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = src
```

`alembic/env.py` loads `src/env/sandbox.env` or `prod.env` from `UPSTOX_ALEMBIC_ENV` (default `demo`), builds `sqlite:///{DB_PATH}`, imports `db.models`, and sets `render_as_batch=True`. **Do not import `helper_func.config` from Alembic** (it requires `--env`).

`alembic/script.py.mako` includes `import sqlmodel` so autogenerated revisions that use `sqlmodel.sql.sqltypes.AutoString` run cleanly.

Run all Alembic commands from the **repo root**. Set `$env:UPSTOX_ALEMBIC_ENV="demo"` (sandbox) or `"prod"` before each command. Do not point demo and prod at the same `.db` file.

### Create a new migration

1. Edit the SQLModel class under `src/db/models/`.
2. Ensure the class is imported from `db.models` (and thus from `alembic/env.py`).
3. Autogenerate a revision:

```powershell
$env:UPSTOX_ALEMBIC_ENV="demo"
uv run alembic revision --autogenerate -m "describe change"
```

4. **Open the new file under `alembic/versions/`.** Autogenerate misses renames, some type tweaks, and data backfills. Fix `upgrade()` / `downgrade()` by hand if needed (e.g. add `server_default` for new NOT NULL columns on existing rows).

### Run migration

Apply all pending revisions to the DB:

```powershell
$env:UPSTOX_ALEMBIC_ENV="demo"
uv run alembic upgrade head
```

Check where the DB is:

```powershell
$env:UPSTOX_ALEMBIC_ENV="demo"
uv run alembic current
uv run alembic history
```

### Undo migration

Roll back **one** revision (runs that revision’s `downgrade()`):

```powershell
$env:UPSTOX_ALEMBIC_ENV="demo"
uv run alembic downgrade -1
```

Roll back to a specific revision id (from `alembic history`):

```powershell
$env:UPSTOX_ALEMBIC_ENV="demo"
uv run alembic downgrade 5ca050ad2e20
```

Alembic records applied revisions in an `alembic_version` table in the same SQLite file. First revision `5ca050ad2e20` creates `order_details`, `stock_table`, and `api_logs`; `7137663ed464` adds `buy_amount` / `sell_amount` on `stock_table`.

### Rules for this project


| Do                                                              | Do not                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Own schema with Alembic after the first real table              | Rely on `SQLModel.metadata.create_all()` to add columns                      |
| Keep using `db_session()` / SQLModel `Session` for **data**     | Mix `CREATE TABLE IF NOT EXISTS` in app code with Alembic on the same tables |
| Review every autogenerated revision                             | Delete the prod `.db` to “fix” schema                                        |
| Wipe the demo `.db` only while the schema is still experimental | Import `helper_func.config` from `alembic/env.py`                            |


While you are still iterating in demo, deleting `src/db/data/trades.db` and running `alembic upgrade head` is fine. Once you care about existing trades, use Alembic only.