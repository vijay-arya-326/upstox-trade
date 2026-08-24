from traceback import print_tb
from typing import Dict

import requests
from requests.exceptions import HTTPError
from helper_func.fancy_print import fancy_print, print_json
from helper_func.constants import CALCULATE_BROKERAGE_URL
from helper_func.config import UPSTOX_URL, UPSTOX_ACCESS_TOKEN, INSTRUMENT_KEY
from helper_func.upstox_requests import login

def headers():
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
    }

def calculate_brokerage(order_obj):
    try:

        query_string = ""
        for key, value in order_obj.items():
            query_string += f"{key}={value}&"

        final_url = f"{UPSTOX_URL}{CALCULATE_BROKERAGE_URL}?{query_string}"

        api_response  =  requests.get(url=final_url, headers=headers())
        if api_response.status_code == 200:
            fancy_print(msg=str(api_response.json()), border_color="green", title="Brokerage Calculation")
    except HTTPError as http_err:
        if api_response.status_code == 401:
            if login():
                calculate_brokerage(order_obj=order_obj)
        else:
            fancy_print(str(http_err), border_color="red", title="Unable to fetch charges - HTTP Error")
            # print_json(data=order_obj, indent=2)
            # print_json(data=book_order.json(), indent=2)
    except Exception as err:
      fancy_print(str(err), border_color="red", title="Unable to fetch charges - Unknown Error")
      print_json(data=str(api_response.json()), indent=2)
      return False
