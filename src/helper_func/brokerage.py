import requests
from requests.exceptions import HTTPError
from helper_func.fancy_print import fancy_print, print_json
from constants import CALCULATE_BROKERAGE_URL
from config import UPSTOX_URL, UPSTOX_ACCESS_TOKEN
from helper_func.upstox_requests import login

def headers():
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
    }

def calculate_brokerage():
    try:
        order_obj = {

        }
        final_url = f"{UPSTOX_URL}{CALCULATE_BROKERAGE_URL}?"
        api_response  =  requests.get(url=final_url, headers=headers())
        api_response.raise_for_status()

    except HTTPError as http_err:
        if api_response.status_code == 401:
            login()
            calculate_brokerage()
        else:
            fancy_print(str(http_err), border_color="red", title="Unable to fetch charges - HTTP Error")
            # print_json(data=order_obj, indent=2)
            # print_json(data=book_order.json(), indent=2)
    except Exception as err:
      fancy_print(str(err), border_color="red", title="Unable to fetch charges - Unknown Error")
      print_json(data=api_response.json(), indent=2)
      return False
