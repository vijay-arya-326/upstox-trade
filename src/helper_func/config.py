import os
from pathlib import Path

APPNAME = os.getenv("APPNAME")
assets_path = Path(__file__).parent.parent
instrument_file = assets_path.joinpath(os.getenv("INSTRUMENT_FILE"))
instrument_pickle_file = assets_path.joinpath(os.getenv("INSTRUMENT_FILE_PICKEL"))






