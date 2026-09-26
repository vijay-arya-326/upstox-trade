#!/usr/bin/env python
"""Launch the HTML UI (backend API + separate frontend/)."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "src"))

os.environ.setdefault("UPSTOX_ENV", "demo")

from web.server import run

if __name__ == "__main__":
    run(host=os.getenv("WEB_HOST", "127.0.0.1"), port=int(os.getenv("WEB_PORT", "8000")))
