import os
from traceback import print_tb
from typing import Dict

import requests
from requests.exceptions import HTTPError
from helper_func.fancy_print import fancy_print, print_json
from helper_func.constants import CALCULATE_BROKERAGE_URL
from helper_func.config import UPSTOX_URL, UPSTOX_ACCESS_TOKEN, INSTRUMENT_KEY, headers_fun
from helper_func.logger import api_logger
from helper_func.upstox_requests import login



def calculate_brokerage(order_obj):
    try:
        query_string = ""
        for key, value in order_obj.items():
            query_string += f"{key}={value}&"

        final_url = f"{UPSTOX_URL}{CALCULATE_BROKERAGE_URL}?{query_string}"
        headers = headers_fun()
        api_response  =  requests.get(url=final_url, headers=headers)
        if api_response.status_code == 200:
            json_response = api_response.json()
            fancy_print(msg=str(json_response), border_color="green", title="Brokerage Calculation")
            return {
                "success": True,
                "data": json_response["data"]
            }

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
    finally:
        api_logger(url=final_url, headers= headers, api_response=api_response, payload=order_obj, method="GET")


def calculate_tax(taxable_profit):
    try:
        taxable_profit = float(taxable_profit)
        total_tax_payable = (taxable_profit * 0.30) * 1.04
        border_color = "green" if total_tax_payable >= 0 else "yellow"
        fancy_print(msg=str(total_tax_payable), border_color=border_color, title="Tax Calculation")
        return total_tax_payable
    except Exception as err:
        fancy_print(str(err), border_color="red", title="Unable to calculate tax - Unknown Error")
        return False
