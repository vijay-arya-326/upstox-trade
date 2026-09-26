import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

from core.config.constants import SANDBOX_ENV_NAME


_initialized = False
_args = None


def _get_fancy_print():
    from core.logging.fancy import fancy_print
    return fancy_print


def check_env_variables():
    error_flag = False
    error_messages = []
    warning_messages = []

    mandatory_variables = [
        "APPNAME",
        "LOADED_ENV",
        "INSTRUMENT_FILE",
        "INSTRUMENT_FILE_PICKLE",
        "SANDBOX_UPSTOX_URL",
        "UPSTOX_URL",
        "UPSTOX_HF_API_URL",
        "UPSTOX_ACCESS_TOKEN",
        "UPSTOX_EXTENDED_TOKEN",
        "UPSTOX_CLIENT_ID",
        "UPSTOX_CLIENT_SECRET",
        "SANDBOX_ACCESS_TOKEN",
        "SEGMENT",
        "SEGMENT_OF_INDEX",
        "UNDERLYING_SYMBOL",
        "UNDERLYING_SYMBOL_OF_INDEX",
        "EXPIRY_DATE",
        "LOTS",
        "DB_PATH",
        "STOP_LOSS_PERCENTAGE",
        "STOP_LOSS_DIFFERENCE_BEFORE_UPDATE",
    ]

    optional_variables = []

    for var in mandatory_variables:
        if not (os.getenv(var) or "").strip():
            error_flag = True
            error_messages.append(f'Mandatory environment variable "{var}" is not set.')

    for var in optional_variables:
        if not (os.getenv(var) or "").strip():
            warning_messages.append(f'Optional Environment Variable "{var}" Missing')

    expiry_date = (os.getenv("EXPIRY_DATE") or "").strip()
    if expiry_date and expiry_date < __import__("datetime").datetime.now().strftime("%Y-%m-%d"):
        error_flag = True
        error_messages.append(f'Expiry date "{expiry_date}" is in the past.')

    sl_per = float(os.getenv("STOP_LOSS_PERCENTAGE", 0))

    if sl_per > 1 or sl_per < 0:
        error_flag = True
        error_messages.append("STOP_LOSS_PERCENTAGE should be between 0 and 1.")

    return {"error_flag": error_flag, "error_messages": error_messages, "warning_messages": warning_messages}


def check_pre_env():
    fancy_print = _get_fancy_print()
    env_checking_response = check_env_variables()

    if env_checking_response["warning_messages"]:
        for message in env_checking_response["warning_messages"]:
            fancy_print(message, border_color="yellow")

    if env_checking_response["error_messages"]:
        for message in env_checking_response["error_messages"]:
            fancy_print(message, border_color="red")

    if env_checking_response["error_flag"]:
        fancy_print("Add and Update Mandatory Environment Variables in .env file and restart the application", border_color="red")
        exit(1)


def init_settings(env: str = None):
    """Initialize settings from command line or explicit env parameter."""
    global _initialized, _args
    
    if _initialized:
        return
    
    parser = argparse.ArgumentParser(description="A script process UPSTOX orders. Pass env PROD|DEMO")
    parser.add_argument("--env", type=str, required=True, help="Demo or Prod env", choices=["prod", "demo"])
    
    if env:
        _args = parser.parse_args(["--env", env])
    else:
        _args = parser.parse_args()
    
    env_file_name = "sandbox.env"
    if _args.env.lower() == "prod":
        env_file_name = "prod.env"
    
    env_file_path = Path(__file__).parent.parent.parent.joinpath("env", env_file_name).resolve()
    if env_file_path.exists():
        load_dotenv(dotenv_path=env_file_path, override=True)
        check_pre_env()
    else:
        exit(f"Env file not found. Create a file at {env_file_path}")
    
    _populate_globals_from_env()
    _initialized = True


def _populate_globals_from_env():
    """Populate global variables from environment after init_settings is called."""
    global ENV_PATH, APPNAME, instrument_file, instrument_pickle_file
    global SANDBOX_UPSTOX_URL, UPSTOX_API_URL, UPSTOX_HF_API_URL
    global LOADED_ENV, SANDBOX_ACCESS_TOKEN
    global UPSTOX_CLIENT_ID, UPSTOX_CLIENT_SECRET, ACCESS_TOKEN
    global UPSTOX_REDIRECT_URI, UPSTOX_ACCESS_TOKEN
    global ORDER_RETRY_COUNT
    global SEGMENT, SEGMENT_OF_INDEX, UNDERLYING_SYMBOL, UNDERLYING_SYMBOL_OF_INDEX, EXPIRY_DATE
    global STOP_LOSS_PERCENTAGE, STOP_LOSS_DIFFERENCE_BEFORE_UPDATE
    global INSTRUMENT_KEY, DB_PATH_FULL
    
    base_path = Path(__file__).parent.parent.parent
    env_file_name = "sandbox.env" if _args.env != "prod" else "prod.env"
    
    ENV_PATH = base_path.joinpath("env", env_file_name).resolve()
    APPNAME = os.getenv("APPNAME")
    instrument_file = base_path.joinpath(os.getenv("INSTRUMENT_FILE"))
    instrument_pickle_file = base_path.joinpath(os.getenv("INSTRUMENT_FILE_PICKLE"))
    SANDBOX_UPSTOX_URL = os.getenv("SANDBOX_UPSTOX_URL")
    UPSTOX_API_URL = os.getenv("UPSTOX_URL")
    UPSTOX_HF_API_URL = os.getenv("UPSTOX_HF_API_URL")
    LOADED_ENV = os.getenv("LOADED_ENV")
    SANDBOX_ACCESS_TOKEN = os.getenv("SANDBOX_ACCESS_TOKEN")
    UPSTOX_CLIENT_ID = os.getenv("UPSTOX_CLIENT_ID")
    UPSTOX_CLIENT_SECRET = os.getenv("UPSTOX_CLIENT_SECRET")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI")
    UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
    ORDER_RETRY_COUNT = 0
    SEGMENT = os.getenv("SEGMENT")
    SEGMENT_OF_INDEX = os.getenv("SEGMENT_OF_INDEX")
    UNDERLYING_SYMBOL = os.getenv("UNDERLYING_SYMBOL")
    UNDERLYING_SYMBOL_OF_INDEX = os.getenv("UNDERLYING_SYMBOL_OF_INDEX")
    EXPIRY_DATE = os.getenv("EXPIRY_DATE")
    STOP_LOSS_PERCENTAGE = float(os.getenv("STOP_LOSS_PERCENTAGE"))
    STOP_LOSS_DIFFERENCE_BEFORE_UPDATE = int(os.getenv("STOP_LOSS_DIFFERENCE_BEFORE_UPDATE"))
    INSTRUMENT_KEY = "NSE_FO|115242"
    DB_PATH_FULL = base_path.joinpath(os.getenv("DB_PATH"))
    
    if not DB_PATH_FULL.exists():
        DB_PATH_FULL.parent.mkdir(parents=True, exist_ok=True)
        DB_PATH_FULL.touch(exist_ok=True)
        print(f"Database path created at {DB_PATH_FULL}")


def headers_fun():
    """Return only prod token"""
    UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
    }


def prepare_headers(live_headers=False):
    """Return prod or sandbox token, based on selected environment"""
    if LOADED_ENV in SANDBOX_ENV_NAME and live_headers == False:
        token = os.environ.get('SANDBOX_ACCESS_TOKEN')
    else:
        token = os.environ.get('UPSTOX_ACCESS_TOKEN')

    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# Backward compatibility - these will be populated after init_settings()
ENV_PATH = None
APPNAME = None
instrument_file = None
instrument_pickle_file = None
SANDBOX_UPSTOX_URL = None
UPSTOX_API_URL = None
UPSTOX_HF_API_URL = None
LOADED_ENV = None
SANDBOX_ACCESS_TOKEN = None
UPSTOX_CLIENT_ID = None
UPSTOX_CLIENT_SECRET = None
ACCESS_TOKEN = None
UPSTOX_REDIRECT_URI = None
UPSTOX_ACCESS_TOKEN = None
ORDER_RETRY_COUNT = 0
SEGMENT = None
SEGMENT_OF_INDEX = None
UNDERLYING_SYMBOL = None
UNDERLYING_SYMBOL_OF_INDEX = None
EXPIRY_DATE = None
STOP_LOSS_PERCENTAGE = None
STOP_LOSS_DIFFERENCE_BEFORE_UPDATE = None
INSTRUMENT_KEY = "NSE_FO|115242"
DB_PATH_FULL = None