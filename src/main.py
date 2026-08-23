from DTO.order_model import OrderModel
from bootstrap.pre_load_check import check_pre_env
import sys
from helper_func.config import APPNAME, LOADED_ENV, ENV_PATH, INSTRUMENT_KEY
from helper_func.download_assets import download_nse_file
from helper_func.fancy_print import fancy_print
from helper_func.manage_login import check_user_auth, validate_sandbox_token
from helper_func.constants import SANDBOX_ENV_NAME
from helper_func.order_helper import place_order, get_order_detail, cancel_order

if __name__ == "__main__":
    fancy_print(APPNAME, border_color="green")
    download_nse_file()
    check_user_auth()
    if LOADED_ENV in SANDBOX_ENV_NAME:
        if not validate_sandbox_token():
            sys.exit(1)

    # sample_order_obj: OrderModel = {
    #   "quantity": 65,
    #   "product": "D",
    #   "validity": "DAY",
    #   "price": 0,
    #   "tag": "entry",
    #   "instrument_token": INSTRUMENT_KEY,
    #   "order_type": "MARKET",
    #   "transaction_type": "BUY",
    #   "disclosed_quantity": 0,
    #   "trigger_price": 0.0,
    #   "is_amo": False,
    #   "slice": True
    # }
    #
    # place_order(sample_order_obj)

    # get_order_detail(order_id=260823101630173)
    cancel_order(order_id=260823140026208)
