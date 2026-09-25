from datetime import datetime
from requests import get
from requests.exceptions import HTTPError

from core.orders.executor import prepare_url
from core.config.settings import prepare_headers, INSTRUMENT_KEY
from core.config.constants import MARKET_QUOTE
from core.logging.fancy import fancy_print, print_json


def getMarketData(instrument_token: str = INSTRUMENT_KEY):
    url = prepare_url(force_live_url=True)
    final_url = f"{url}{MARKET_QUOTE}{instrument_token}"
    headers = prepare_headers(live_headers=True)

    try:
        api_response = get(url=final_url, headers=headers)
        api_response.raise_for_status()
        if api_response.status_code == 200:
            response = api_response.json()

            data = response['data']
            key = next(iter(data))
            last_price = data[key]['last_price']

            print(f"Last Traded Price :: {last_price} for instrument {instrument_token} @ { datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except HTTPError as http_err:
        fancy_print(str(http_err), border_color="red", title="Market Data Retrieval Failed - Http Error")
    except Exception as err:
        fancy_print(str(err), border_color="red", title="Market Data Retrieval Failed - Unknown Error")
        print_json(data=headers)
        return False