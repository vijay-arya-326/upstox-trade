import os
from pathlib import Path

APPNAME = os.getenv("APPNAME")
assets_path = Path(__file__).parent.parent
instrument_file = assets_path.joinpath(os.getenv("INSTRUMENT_FILE"))
instrument_pickle_file = assets_path.joinpath(os.getenv("INSTRUMENT_FILE_PICKEL"))

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

ORDER_RETRY_COUNT = 3

# Setting up envPath
if LOADED_ENV == "DEMO":
    ENV_PATH =  assets_path.joinpath("env").joinpath("sandbox.env")
else:
    ENV_PATH = assets_path.joinpath("env").joinpath("prod.env")


