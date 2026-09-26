"""HTML-UI backend: stdlib-only HTTP API + static frontend server.

Serves ../frontend/ (repo-root /frontend) and exposes /api/* JSON endpoints
bridging the existing core (strategies, persistence, market quotes).
No new third-party dependencies.
"""
import json
import os
import sys
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FRONTEND_SRC = REPO_ROOT / "frontend"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
# Serve the built React bundle when present, else the raw frontend dir (dev).
FRONTEND_DIR = FRONTEND_DIST if (FRONTEND_DIST / "index.html").exists() else FRONTEND_SRC
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

ENGINE_STATE = {"running": False, "strategy": os.getenv("STRATEGIES", "UT_BOT"),
                 "instrument_key": os.getenv("INSTRUMENT_KEY", "NSE_FO|115242")}

_settings_ok = None
_instruments = None


def _load_instruments():
    """Lazy-load NSE instrument master once; keep only UI-needed fields."""
    global _instruments
    if _instruments is not None:
        return _instruments
    keep = ("instrument_key", "trading_symbol", "name", "segment",
            "instrument_type", "lot_size", "tick_size", "exchange")
    for cand in (REPO_ROOT / "src" / "assets" / "NSE.json", SRC_ROOT / "assets" / "NSE.json"):
        if cand.exists():
            with open(cand) as f:
                raw = json.load(f)
            _instruments = [{k: r.get(k) for k in keep} for r in raw]
            break
    else:
        _instruments = []
    return _instruments


def api_segments():
    data = _load_instruments()
    return {"segments": sorted({r["segment"] for r in data if r.get("segment")}),
            "count": len(data)}


def api_instruments(q="", segment="", limit=50):
    data = _load_instruments()
    if segment:
        data = [r for r in data if r.get("segment") == segment]
    if q:
        ql = q.strip().lower()
        data = [r for r in data
                if ql in str(r.get("trading_symbol") or "").lower()
                or ql in str(r.get("name") or "").lower()]
    try:
        limit = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        limit = 50
    return {"data": data[:limit], "total": len(data)}


def _ensure_settings():
    global _settings_ok
    if _settings_ok is not None:
        return _settings_ok
    try:
        from core.config.settings import init_settings
        init_settings(os.environ.get("UPSTOX_ENV", "demo"))
        _settings_ok = True
    except SystemExit as e:
        _settings_ok = f"settings exit: {e}"
    except Exception as e:  # missing env file, bad env, etc.
        _settings_ok = str(e)
    return _settings_ok


def _rows(model_name, limit=100):
    """Fetch latest rows for a persistence model; graceful fallback."""
    ok = _ensure_settings()
    if ok is not True:
        return [], f"settings not initialized: {ok}"
    try:
        from core.persistence.db import orm_session
        from core.persistence import models as m
        from sqlmodel import select
        model = getattr(m, model_name)
        with orm_session() as s:
            rows = s.exec(select(model).order_by(model.id.desc()).limit(limit)).all()
            return [r.model_dump() if hasattr(r, "model_dump") else dict(r) for r in rows], None
    except Exception as e:
        return [], str(e)


def api_status():
    ok = _ensure_settings()
    strategies = []
    try:
        from strategy.registry import STRATEGIES
        strategies = sorted(STRATEGIES.keys())
    except Exception:
        pass
    status = {
        "app": "upstox-trade",
        "env": os.environ.get("UPSTOX_ENV", "demo"),
        "strategies": strategies,
        "engine": ENGINE_STATE,
        "settings": "ok" if ok is True else str(ok),
    }
    try:
        from core.config import settings as st
        status["instrument_key"] = getattr(st, "INSTRUMENT_KEY", None)
        dbp = getattr(st, "DB_PATH_FULL", None)
        status["db_path"] = str(dbp) if dbp else None
    except Exception:
        pass
    return status


_ltp_cache = {}  # instrument_key -> (timestamp, payload)
LTP_TTL = 15


def api_ltp(instrument_key=None):
    import time
    ok = _ensure_settings()
    if ok is not True:
        return {"ltp": None, "live": False, "error": f"settings: {ok}"}
    try:
        from core.market import getMarketData as _gmd  # noqa
        from core.market.quotes import getMarketData
        key = instrument_key
        if not key:
            from core.config import settings as st
            key = getattr(st, "INSTRUMENT_KEY", None)
        now = time.time()
        hit = _ltp_cache.get(key)
        if hit and now - hit[0] < LTP_TTL:
            return {**hit[1], "cached": True}
        # NOTE: current getMarketData prints LTP but returns None on success.
        result = getMarketData(instrument_token=key)
        ltp = result if isinstance(result, (int, float)) else None
        payload = {"ltp": ltp, "live": ltp is not None, "instrument_key": key,
                   "note": "quote bridge returns None until quotes.py returns price"}
        _ltp_cache[key] = (now, payload)
        return payload
    except Exception as e:
        return {"ltp": None, "live": False, "error": str(e)}


class Handler(BaseHTTPRequestHandler):
    server_version = "upstox-web/0.1"

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path):
        rel = path.lstrip("/") or "index.html"
        target = (FRONTEND_DIR / rel).resolve()
        if not str(target).startswith(str(FRONTEND_DIR.resolve())):
            self.send_response(404)
            self.end_headers()
            return
        if not target.is_file():
            # SPA fallback: unknown paths serve index.html (except /api/*, handled earlier)
            target = FRONTEND_DIR / "index.html"
        import mimetypes
        ctype, _ = mimetypes.guess_type(str(target))
        if ctype is None:
            ctype = "application/octet-stream"
        if ctype.startswith("text/") and "charset" not in ctype:
            ctype += "; charset=utf-8"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/status":
            return self._send_json(api_status())
        if u.path == "/api/strategies":
            st = api_status()
            return self._send_json({"strategies": st["strategies"], "mode_env": os.getenv("STRATEGY_MODE", "majority")})
        if u.path == "/api/positions":
            data, err = _rows("Position")
            return self._send_json({"data": data, "error": err})
        if u.path == "/api/orders":
            data, err = _rows("OrderDetail")
            return self._send_json({"data": data, "error": err})
        if u.path == "/api/signals":
            data, err = _rows("SignalLog")
            return self._send_json({"data": data, "error": err})
        if u.path == "/api/ltp":
            return self._send_json(api_ltp((q.get("instrument_key") or [None])[0]))
        if u.path == "/api/instruments/segments":
            return self._send_json(api_segments())
        if u.path == "/api/instruments":
            return self._send_json(api_instruments(
                (q.get("q") or [""])[0],
                (q.get("segment") or [""])[0],
                (q.get("limit") or [50])[0]))
        return self._serve_static(u.path)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/engine":
            try:
                n = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                payload = {}
            action = payload.get("action")
            if action == "start":
                ENGINE_STATE["running"] = True
            elif action == "stop":
                ENGINE_STATE["running"] = False
            if payload.get("strategy"):
                ENGINE_STATE["strategy"] = payload["strategy"]
            if payload.get("instrument_key"):
                ENGINE_STATE["instrument_key"] = payload["instrument_key"]
            return self._send_json({"ok": True, "engine": ENGINE_STATE})
        self.send_response(404)
        self.end_headers()

    def log_message(self, *a):
        pass


def run(host="127.0.0.1", port=8000):
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"upstox-trade web: http://{host}:{port}  (frontend: {FRONTEND_DIR})")
    srv.serve_forever()


if __name__ == "__main__":
    run(host=os.getenv("WEB_HOST", "127.0.0.1"), port=int(os.getenv("WEB_PORT", "8000")))
