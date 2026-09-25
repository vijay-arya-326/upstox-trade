import sys
import os

from core.config.settings import init_settings, APPNAME, LOADED_ENV, INSTRUMENT_KEY, SANDBOX_ENV_NAME
from core.market import download_nse_file
from core.auth import check_user_auth, validate_sandbox_token
from core.persistence.db import db_session
from core.logging.fancy import fancy_print
from engine import StrategyEngine
from strategy.registry import build_composite


if __name__ == "__main__":
    env = os.environ.get("UPSTOX_ENV") or "demo"
    init_settings(env)
    
    strategy = build_composite()
    engine = StrategyEngine(strategy, instrument_key=INSTRUMENT_KEY)
    engine.run()