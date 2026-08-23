from pygments.lexers import data

from DTO.order_model import OrderModel
from helper_func.constants import PLACE_ORDER_URL, SANDBOX_ENV_NAME
from helper_func.config import (LOADED_ENV, UPSTOX_URL, SANDBOX_UPSTOX_URL, UPSTOX_HF_API_URL, ACCESS_TOKEN,
 SANDBOX_ACCESS_TOKEN, ORDER_RETRY_COUNT)
from requests import post, get
from requests.exceptions import HTTPError
from helper_func.fancy_print import fancy_print, print_json
from helper_func.upstox_requests import login

def place_order(order_obj: OrderModel, retry_count:int= 0):
    if LOADED_ENV in SANDBOX_ENV_NAME:
        url = SANDBOX_UPSTOX_URL
        token = SANDBOX_ACCESS_TOKEN
    else:
        url = UPSTOX_HF_API_URL
        token = ACCESS_TOKEN

    final_url =  url+PLACE_ORDER_URL
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        book_order = post(url=final_url, headers=headers, json=order_obj)
        book_order.raise_for_status()
        print(book_order.json())
        return True
    except HTTPError as http_err:
        if book_order.status_code == 401:
            # TODO: attemp relogin and recall function
            login()
            # try login for upstox request after login
            if retry_count <= ORDER_RETRY_COUNT:
                place_order(order_obj, retry_count + 1)
            else:
                fancy_print("All retry failed", border_color="red")
                return False
        else:
            fancy_print(str(http_err), border_color="red")
            print_json(data=order_obj, indent=2)
            print_json(data=book_order.json(), indent=2)
            return False
    except Exception as err:
        fancy_print(str(err) , border_color="red")
        print_json(data=headers)
        return False

def modify_order():
    pass

def close_order():
    pass

def list_order():
    pass
