from DTO.order_model import OrderModel, ModifyOrderModel
from bootstrap.pre_load_check import check_pre_env
import sys

from db.helper.db_connector import db_session
from helper_func.brokerage import calculate_brokerage
from helper_func.config import APPNAME, LOADED_ENV, ENV_PATH, INSTRUMENT_KEY
from helper_func.download_assets import download_nse_file
from helper_func.fancy_print import fancy_print
from helper_func.manage_login import check_user_auth, validate_sandbox_token
from helper_func.constants import SANDBOX_ENV_NAME
from helper_func.order_helper import place_order, get_order_detail, cancel_order, modify_order
from db.helper.db_connector import db_session

if __name__ == "__main__":
    fancy_print(APPNAME, border_color="green")
    download_nse_file()
    check_user_auth()
    if LOADED_ENV in SANDBOX_ENV_NAME:
        if not validate_sandbox_token():
            sys.exit(1)

    with db_session() as session:
        session.execute("Select 1;")
        fancy_print(msg="DB Connected", title="DB Connected", border_color="green")


    # order_obj_buy = {
    #     "instrument_token": INSTRUMENT_KEY,
    #     "product": "D",
    #     "quantity": 65,
    #     "transaction_type": "BUY",
    #     "price": 11000
    # }
    #
    # calculate_brokerage(order_obj= order_obj_buy)
    #
    # order_obj_sell = {
    #     "instrument_token": INSTRUMENT_KEY,
    #     "product": "D",
    #     "quantity": 65,
    #     "transaction_type": "SELL",
    #     "price": 12000
    # }
    #
    # calculate_brokerage(order_obj=order_obj_sell)
