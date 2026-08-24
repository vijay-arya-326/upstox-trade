import os
from pathlib import Path
import argparse
from dotenv import load_dotenv
from bootstrap.pre_load_check import check_pre_env
import sys

#Loading env file
# 1. Initialize the parser
parser = argparse.ArgumentParser(description="A script process UPSTOX orders. Pass env PROD|DEMO")
# 2. Add named arguments
parser.add_argument("--env", type=str, required=True, help="Demo or Prod env", choices=["prod", "demo"])
# 3. Parse the arguments
args = parser.parse_args()

env_file_name = "sandbox.env"
#LOAD ENV Based on passed arguments
if args.env.lower() == "prod":
    env_file_name="prod.env"

env_file_path = Path(__file__).parent.parent.joinpath("env", env_file_name).resolve()
if env_file_path.exists():
    load_dotenv(dotenv_path=env_file_path, override=True)
    check_pre_env()
else:
    exit(f"Env file not found. Create a file at {env_file_path}")

#################

ENV_PATH = env_file_path
APPNAME = os.getenv("APPNAME")
assets_path = Path(__file__).parent.parent
instrument_file = assets_path.joinpath(os.getenv("INSTRUMENT_FILE"))
instrument_pickle_file = assets_path.joinpath(os.getenv("INSTRUMENT_FILE_PICKLE"))

SANDBOX_UPSTOX_URL = os.getenv("SANDBOX_UPSTOX_URL")
UPSTOX_URL = os.getenv("UPSTOX_URL")
UPSTOX_HF_API_URL = os.getenv("UPSTOX_HF_API_URL")

LOADED_ENV = os.getenv("LOADED_ENV")

SANDBOX_ACCESS_TOKEN = os.getenv("SANDBOX_ACCESS_TOKEN")

UPSTOX_CLIENT_ID = os.getenv("UPSTOX_CLIENT_ID")
UPSTOX_CLIENT_SECRET =  os.getenv("UPSTOX_CLIENT_SECRET")
ACCESS_TOKEN =  os.getenv("ACCESS_TOKEN")

UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI")

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

ORDER_RETRY_COUNT = 0

SEGMENT = os.getenv("SEGMENT")
SEGMENT_OF_INDEX = os.getenv("SEGMENT_OF_INDEX")
UNDERLYING_SYMBOL = os.getenv("UNDERLYING_SYMBOL")
UNDERLYING_SYMBOL_OF_INDEX = os.getenv("UNDERLYING_SYMBOL_OF_INDEX")
EXPIRY_DATE = os.getenv("EXPIRY_DATE")

# INSTRUMENT_KEY =  f"{SEGMENT_OF_INDEX}|{UNDERLYING_SYMBOL_OF_INDEX}"
INSTRUMENT_KEY =  "NSE_FO|61703"

DB_PATH_FULL = Path(__file__).parent.parent.joinpath(os.getenv("DB_PATH"))

if not DB_PATH_FULL.exists():
    DB_PATH_FULL.mkdir(parents=True, exist_ok=True)
    print(f"Database path created at {DB_PATH_FULL}")
