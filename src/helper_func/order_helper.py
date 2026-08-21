from DTO.order_model import OrderModel
from constants import PLACE_ORDER_URL
from config import (LOADED_ENV, UPSTOX_URL, SANDBOX_UPSTOX_URL, UPSTOX_HF_API_URL, ACCESS_TOKEN,
 SANDBOX_ACCESS_TOKEN, ORDER_RETRY_COUNT)
from requests import post, get
from requests.exceptions import HTTPError
from helper_func.fancy_print import fancy_print, print_json
from helper_func.upstox_requests import login

def place_order(order_obj: OrderModel, retry_count:int= 0):
    if LOADED_ENV == "DEMO":
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
        book_order = post(url=final_url, headers=headers, data=order_obj)
        book_order.raise_for_status()
        return True
    except HTTPError as http_err:
        if book_order.status_code == 401:
            # TODO: attemp relogin and recall function
            # try login for upstox request
            if retry_count <= ORDER_RETRY_COUNT:
                place_order(order_obj, retry_count + 1)
            else:
                fancy_print("All retry failed", border_color="red")
                return False
            pass
        else:
            fancy_print(str(http_err) + final_url, border_color="red")
            print_json(data=headers)
            return False
    except Exception as err:
        fancy_print(str(err) +"\n"+ final_url, border_color="red")
        print_json(data=headers)
        return False

def modify_order():
    pass

def close_order():
    pass

def list_order():
    pass
