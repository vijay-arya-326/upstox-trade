import pickle

from core.logging.fancy import fancy_print
from datetime import datetime
import os
import requests
import gzip
import json


def _get_instrument_paths():
    from core.config.settings import instrument_file, instrument_pickle_file
    return instrument_file, instrument_pickle_file


def download_nse_file():
    url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
    instrument_file, instrument_pickle_file = _get_instrument_paths()
    output_filename = instrument_file
    pickle_filePath = instrument_pickle_file
    if os.path.exists(output_filename):
        file_mod_date = datetime.fromtimestamp(os.path.getmtime(output_filename)).date()
        if file_mod_date == datetime.now().date():
            fancy_print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"File '{output_filename}' is already up to date for today. Skipping download.",
                        border_color="bright_yellow")
            return

    fancy_print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching fresh daily NSE master data...",
                border_color="green")

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        decompressed_data = gzip.decompress(response.content)
        json_data = json.loads(decompressed_data.decode('utf-8'))

        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)

        fancy_print(f"Successfully saved {len(json_data)} instruments to '{output_filename}'", border_color="green")

        if os.path.exists(pickle_filePath):
            os.remove(pickle_filePath)
        create_pkl_file()

    except requests.exceptions.RequestException as e:
        fancy_print(f"Network error while downloading: {e}", border_color="red")
    except Exception as e:
        fancy_print(f"An unexpected error occurred: {e}", border_color="red")


def create_pkl_file():
    instrument_file, instrument_pickle_file = _get_instrument_paths()
    with open(instrument_file, 'r') as f:
        data = json.load(f)

    with open(instrument_pickle_file, 'wb') as f:
        pickle.dump(data, f)
        fancy_print(f"Successfully saved {len(data)} instruments to '{instrument_pickle_file}'", border_color="blue")