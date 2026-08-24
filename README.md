# upstox-trade

CLI helper for placing and managing [Upstox](https://upstox.com/) orders. It loads a demo or live env file, downloads the daily NSE instrument dump, checks OAuth tokens (and re-logins in the browser when the live token is expired), then exposes helpers to place, modify, and cancel orders.

Requires **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**.

## Setup with uv

1. Install uv if it is not already on your PATH:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   On Windows, use the installer from the [uv docs](https://docs.astral.sh/uv/getting-started/installation/).

2. Clone the repo and create the virtualenv + install dependencies from `pyproject.toml` / `uv.lock`:

   ```bash
   cd upstox-trade
   uv sync
   ```

   This creates `.venv` in the project root. You can either activate it (`source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\activate` on Windows) or always prefix commands with `uv run`.

3. Copy the env template and fill in credentials. Env files live under `src/env/` and are gitignored (`**/*.env`).

   ```bash
   cp src/env/.env.example src/env/sandbox.env
   cp src/env/.env.example src/env/prod.env
   ```

   `--env=demo` loads `src/env/sandbox.env`. `--env=prod` loads `src/env/prod.env`.

4. In the [Upstox developer app](https://account.upstox.com/developer/apps), set the redirect URI to the **same** value as `UPSTOX_REDIRECT_URI`, for example:

   `http://127.0.0.1:8080/upstox/callback`

   Use IPv4 `127.0.0.1` (not `localhost`) and a port **>= 1024** (do not use 80/443). Avoid 5000 and 7000 on macOS (AirPlay). Register that exact string; the local callback server binds the host and port from this URI.

5. Fill remaining variables (see [Environment variables](#environment-variables)). Paste `SANDBOX_ACCESS_TOKEN` from the Upstox sandbox console. Live `UPSTOX_ACCESS_TOKEN` / `UPSTOX_EXTENDED_TOKEN` are written automatically after browser login.

## Run

From the `src` directory so package imports resolve:

```bash
cd src
uv run main.py --env=demo
```

Live / production:

```bash
cd src
uv run main.py --env=prod
```

`--env` is required and must be `demo` or `prod`.

Startup flow:

1. Print `APPNAME`.
2. Download today's NSE instrument JSON (skip if already fetched today) and pickle it.
3. Validate the **live** access token. If it is expired, open the Upstox login page and capture the OAuth callback on `UPSTOX_REDIRECT_URI`.
4. In demo/sandbox (`LOADED_ENV` is `DEMO` or `SANDBOX`), validate the sandbox token. Exit with status 1 if it is missing or expired (sandbox tokens are pasted by hand).

Order helpers (`place_order`, `modify_order`, `cancel_order`) are imported from `main.py` for use after this bootstrap; they are not invoked automatically.

## Environment variables

Mandatory keys checked at load time (`src/bootstrap/pre_load_check.py`):

| Variable | Purpose |
| --- | --- |
| `APPNAME` | Banner shown at startup |
| `LOADED_ENV` | `DEMO` / `SANDBOX` vs live (`LIVE` / `PROD`) |
| `INSTRUMENT_FILE` | Path to NSE JSON (relative to `src/`), e.g. `assets/NSE.json` |
| `INSTRUMENT_FILE_PICKLE` | Pickle cache path, e.g. `assets/NSE.pkl` |
| `SANDBOX_UPSTOX_URL` | Sandbox API base, typically `https://api-sandbox.upstox.com` |
| `UPSTOX_URL` | Live API base, typically `https://api.upstox.com` |
| `UPSTOX_HF_API_URL` | High-frequency live API, typically `https://api-hft.upstox.com` |
| `UPSTOX_CLIENT_ID` / `UPSTOX_CLIENT_SECRET` | OAuth app credentials |
| `UPSTOX_REDIRECT_URI` | Local callback URL (must match the developer app) |
| `UPSTOX_ACCESS_TOKEN` / `UPSTOX_EXTENDED_TOKEN` | Live tokens (auto-updated after login) |
| `SANDBOX_ACCESS_TOKEN` | Sandbox token (manual) |
| `SEGMENT`, `SEGMENT_OF_INDEX` | Exchange segment labels |
| `UNDERLYING_SYMBOL`, `UNDERLYING_SYMBOL_OF_INDEX` | Underlying identifiers |
| `EXPIRY_DATE` | Contract expiry `YYYY-MM-DD` (must not be in the past) |
| `LOTS` | Lot size used when sizing orders |

`src/env/.env.example` is a starting template; add any keys listed above that are not in the example.

## Project layout

```
upstox-trade/
├── pyproject.toml          # Project metadata and uv dependencies
├── uv.lock                 # Locked dependency versions
├── src/
│   ├── main.py             # Entry point
│   ├── bootstrap/          # Startup env validation
│   ├── DTO/                # Order request models
│   ├── env/                # sandbox.env / prod.env (not committed)
│   ├── assets/             # Downloaded NSE.json / NSE.pkl
│   └── helper_func/        # Config, auth, HTTP, printing
```

### Root

| File | Function |
| --- | --- |
| [`pyproject.toml`](pyproject.toml) | Package name, Python `>=3.12`, dependencies: `dotenv`, `pydantic`, `requests`, `rich`. |
| [`uv.lock`](uv.lock) | Exact versions installed by `uv sync`. |
| [`.gitignore`](.gitignore) | Ignores `.venv`, `**/*.env`, and generated `NSE.json` / `NSE.pkl`. |

### Entry and bootstrap

| File | Function |
| --- | --- |
| [`src/main.py`](src/main.py) | CLI entry: banner, instrument download, live login, sandbox token check in demo. |
| [`src/bootstrap/pre_load_check.py`](src/bootstrap/pre_load_check.py) | Ensures mandatory env vars are set and `EXPIRY_DATE` is not in the past; exits if not. |

### Config, constants, UI

| File | Function |
| --- | --- |
| [`src/helper_func/config.py`](src/helper_func/config.py) | Parses `--env`, loads `sandbox.env` or `prod.env`, runs pre-load checks, exposes API URLs, tokens, and instrument paths. |
| [`src/helper_func/constants.py`](src/helper_func/constants.py) | Upstox path suffixes (login, token, place/modify/cancel order) and sandbox env name aliases. |
| [`src/helper_func/fancy_print.py`](src/helper_func/fancy_print.py) | Rich panels for info / warning / error messages. |

### Auth and market data

| File | Function |
| --- | --- |
| [`src/helper_func/manage_login.py`](src/helper_func/manage_login.py) | `check_user_auth()` probes the live token and calls `login()` if needed; `validate_sandbox_token()` probes the sandbox token. |
| [`src/helper_func/upstox_requests.py`](src/helper_func/upstox_requests.py) | Token probe via place-order endpoint; OAuth browser login; local HTTP callback on the redirect URI (rejects ports &lt; 1024); writes live tokens back into the env file. |
| [`src/helper_func/download_assets.py`](src/helper_func/download_assets.py) | Downloads gzipped NSE instrument master from Upstox assets once per day, writes JSON, rebuilds the pickle cache. |

### Orders

| File | Function |
| --- | --- |
| [`src/DTO/order_model.py`](src/DTO/order_model.py) | Pydantic models: `OrderModel` (place) and `ModifyOrderModel` (modify), with enums and price/trigger/market-protection rules. |
| [`src/helper_func/order_helper.py`](src/helper_func/order_helper.py) | HTTP helpers: `place_order`, `modify_order`, `cancel_order`; picks sandbox vs HFT URL and bearer token from `LOADED_ENV`; retries login on 401. |

### Env and assets

| Path | Function |
| --- | --- |
| [`src/env/.env.example`](src/env/.env.example) | Template for `sandbox.env` / `prod.env` (credentials, URLs, redirect URI). |
| `src/env/sandbox.env` | Demo/sandbox runtime config (local, gitignored). |
| `src/env/prod.env` | Live runtime config (local, gitignored). |
| `src/assets/` | Generated `NSE.json` and `NSE.pkl` from the daily instrument download. |
