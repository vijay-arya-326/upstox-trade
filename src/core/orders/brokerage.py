import os
from traceback import print_tb
from typing import Dict

import requests
from requests.exceptions import HTTPError
from core.logging.fancy import fancy_print, print_json
from core.config.constants import CALCULATE_BROKERAGE_URL
from core.auth import login


def _get_brokerage_settings():
    from core.config.settings import UPSTOX_API_URL, UPSTOX_ACCESS_TOKEN, INSTRUMENT_KEY, headers_fun
    return {
        "UPSTOX_API_URL": UPSTOX_API_URL,
        "UPSTOX_ACCESS_TOKEN": UPSTOX_ACCESS_TOKEN,
        "INSTRUMENT_KEY": INSTRUMENT_KEY,
        "headers_fun": headers_fun,
    }


def _get_api_logger():
    from core.logging import get_api_logger
    return get_api_logger()


def calculate_brokerage(order_obj):
    s = _get_brokerage_settings()
    try:
        query_string = ""
        for key, value in order_obj.items():
            query_string += f"{key}={value}&"

        final_url = f"{s['UPSTOX_API_URL']}{CALCULATE_BROKERAGE_URL}?{query_string}"
        headers = s["headers_fun"]()
        api_response = requests.get(url=final_url, headers=headers)
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
    except Exception as err:
        fancy_print(str(err), border_color="red", title="Unable to fetch charges - Unknown Error")
        print_json(data=str(api_response.json()), indent=2)
        return False
    finally:
        _get_api_logger()(url=final_url, headers=headers, api_response=api_response, payload=order_obj, method="GET")


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