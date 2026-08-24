import json
from calendar import day_name
from math import modf

from DTO.order_model import OrderModel, ModifyOrderModel
from helper_func.constants import PLACE_ORDER_URL, SANDBOX_ENV_NAME, CANCEL_ORDER_URL, MODIFY_ORDER_URL
from helper_func.config import (LOADED_ENV, UPSTOX_URL, SANDBOX_UPSTOX_URL, UPSTOX_HF_API_URL, ACCESS_TOKEN,
 SANDBOX_ACCESS_TOKEN, ORDER_RETRY_COUNT)
from requests import post, get, delete, put
from requests.exceptions import HTTPError
from helper_func.fancy_print import fancy_print, print_json
from helper_func.upstox_requests import login



def prepare_url(support_hf:bool= False):
    if LOADED_ENV in SANDBOX_ENV_NAME:
        url = SANDBOX_UPSTOX_URL
        token = SANDBOX_ACCESS_TOKEN
    else:
        if support_hf:
            url = UPSTOX_HF_API_URL
        else:
            url = UPSTOX_HF_API_URL
        token = ACCESS_TOKEN

    return url

def prepare_headers():
    if LOADED_ENV in SANDBOX_ENV_NAME:
        token = SANDBOX_ACCESS_TOKEN
    else:
        token = ACCESS_TOKEN

    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }


def place_order(order_obj: OrderModel, retry_count:int= 0,):
    try:
        final_url = prepare_url(support_hf=True) + PLACE_ORDER_URL
        headers = prepare_headers()
        book_order = post(url=final_url, headers=headers, json=order_obj)
        book_order.raise_for_status()
        if book_order.status_code == 200:
            order_response = book_order.json()
            fancy_print( str(order_response), border_color="green", title="Order placed Successfully")
            # print_json(data=order_response, indent=2)
            return order_response['data']['order_ids']

    except HTTPError as http_err:
        if book_order.status_code == 401:
            # TODO: attemp relogin and recall function
            if login():
            # try login for upstox request after login
                if retry_count <= ORDER_RETRY_COUNT:
                    place_order(order_obj, retry_count + 1)
                else:
                    fancy_print("All retry failed", border_color="red", title="Order placed Failed - Http Error")
                    return False
        else:
            fancy_print(str(http_err), border_color="red", title="Order placed Failed - Unknown Error")
            print_json(data=order_obj, indent=2)
            print_json(data=book_order.json(), indent=2)
            return False
    except Exception as err:
        fancy_print(str(err) , border_color="red")
        print_json(data=headers)
        return False

def modify_order(order_obj:ModifyOrderModel):
    try:
        headers = prepare_headers()
        headers.update({"Content-Type": "application/json"})
        final_url = prepare_url(support_hf=True) + MODIFY_ORDER_URL
        api_response = put(url=final_url, headers=headers, json=order_obj)
        api_response.raise_for_status()
        if api_response.status_code == 200:
            order_response = api_response.json()
            fancy_print(str(order_response), border_color="green", title="Order Modified Successfully")
    except HTTPError as http_err:
        if api_response.status_code == 401:
            login()
            modify_order(order_obj)
        else:
            fancy_print(str(http_err), border_color="red", title="Order Modification Failed -HTTP Error")
            fancy_print(str(order_obj), border_color="red", title="Failure  Details")
            fancy_print(str(api_response.json()), border_color="red", title="Failure  Details")
            fancy_print(str(headers), border_color="red", title="Failure  Details")
    except Exception as err:
        fancy_print(str(err), border_color="red", title="Order Modification Failed - Unknown Error")
        print_json(data=headers)
        return False


def close_order(order_id: int):
    pass

def cancel_order(order_id :int):
    try:
        url = prepare_url(support_hf=True)
        final_url = f"{url}{CANCEL_ORDER_URL}?order_id={order_id}"
        headers = prepare_headers()
        api_response = delete(url=final_url, headers=headers)
        api_response.raise_for_status()
        if api_response.status_code == 200:
            response = api_response.json()
            fancy_print(str(response), border_color="green", title="Order cancelled Successfully")
    except HTTPError as http_err:
        if api_response.status_code == 401:
            login()
            cancel_order(order_id)
        else:
            fancy_print(str(http_err), border_color="red", title="Order canceled Failed")
    except Exception as err:
        fancy_print(str(err), border_color="red", title="Order canceled Failed - Unknown Error")
        print_json(data=headers)
        return False


def list_order():
    pass

def get_order_detail(order_id: int ):
    try:
        final_url =  prepare_url() + PLACE_ORDER_URL + str(order_id)
        headers = prepare_headers()
        pass
    except HTTPError as http_err:
        login()
        if ORDER_RETRY_COUNT <= ORDER_RETRY_COUNT:
            pass
    except Exception as err:
        fancy_print(str(err), border_color="red")
        print_json(data=headers)
        return False
