from datetime import datetime

from requests import post, get, delete, put
from requests.exceptions import HTTPError

from DTO.order_model import OrderDTOModel, ModifyOrderDTOModel, OrderDetailDTOModel
from db.helper.db_connector import orm_session
from db.models import OrderDetail, Position
from helper_func.brokerage import calculate_brokerage
from helper_func.common_models import TransactionType
from helper_func.config import (
    LOADED_ENV, SANDBOX_UPSTOX_URL, UPSTOX_HF_API_URL, ORDER_RETRY_COUNT, prepare_headers, STOP_LOSS_PERCENTAGE
)
from helper_func.constants import (
    PLACE_ORDER_URL, SANDBOX_ENV_NAME, CANCEL_ORDER_URL, MODIFY_ORDER_URL, ORDER_DETAIL_v2
)
from helper_func.fancy_print import fancy_print, print_json
from helper_func.logger import api_logger
from helper_func.upstox_requests import login
from sample.response import order_detail_sample_response

runSampleOutput = False

placed_order_obj = None

def prepare_url(support_hf:bool= False):
    global runSampleOutput
    if LOADED_ENV in SANDBOX_ENV_NAME:
        url = SANDBOX_UPSTOX_URL
        runSampleOutput = True
    else:
        if support_hf:
            url = UPSTOX_HF_API_URL
        else:
            url = UPSTOX_HF_API_URL
    return url

def place_order(market_price: float |int,  order_obj: OrderDTOModel):
    global placed_order_obj
    try:
        final_url = prepare_url(support_hf=True) + PLACE_ORDER_URL
        headers = prepare_headers()

        order_obj['trigger_price'] = market_price * (1 - STOP_LOSS_PERCENTAGE)

        placed_order_obj = order_obj

        book_order = post(url=final_url, headers=headers, json=order_obj)
        book_order.raise_for_status()
        if book_order.status_code == 200:
            order_response = book_order.json()
            fancy_print( str(order_response), border_color="green", title="Order placed Successfully")
            # print_json(data=order_response, indent=2)
            order_ids = order_response['data']['order_ids']
            for order_id in order_ids:
                fancy_print(msg="Logging - Details", bg_color="yellow", title="Processing Order Details")
                get_order_detail(order_id=order_id)
            fancy_print(msg= "Order Place successfully", border_color="green", title="Order Place Successfully")

    except HTTPError as http_err:
            fancy_print(str(http_err), border_color="red", title="Order placed Failed - HTTP Error")
            print_json(data=order_obj, indent=2)
            print_json(data=book_order.json(), indent=2)
            return False
    except Exception as err:
        fancy_print(str(err) , border_color="red", title="Order placed Failed - Unknown Error")
        print_json(data=headers)
        print_json(data = order_response)
        return False
    finally:
        api_logger(url=final_url, headers= headers, api_response=book_order, payload=order_obj, method="POST")

def modify_order(order_obj:ModifyOrderDTOModel):
    try:
        headers = prepare_headers()
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
    global placed_order_obj
    try:
        final_url =  prepare_url() + ORDER_DETAIL_v2 + str(order_id)
        headers = prepare_headers()
        api_response = get(url=final_url, headers=headers)
        if runSampleOutput == True:
            response =  order_detail_sample_response
        else:
            api_response.raise_for_status()
            response = api_response.json()

        order_response:OrderDetailDTOModel = OrderDetailDTOModel.model_validate(response['data'])

        order = OrderDetail(
            order_id= order_id,
            instrument_token=order_response.instrument_token,
            exchange_type=order_response.exchange,
            product=order_response.product,
            quantity=order_response.quantity,
            filled_qty=order_response.filled_quantity,
            transaction_type=order_response.transaction_type.value,
            price= order_response.average_price,
            validity= order_response.validity,
            order_type=order_response.order_type.value,
            trigger_price=order_response.trigger_price,
            tag=order_response.tag,
            created_at=datetime.now().replace(microsecond=0),
            updated_at=datetime.now().replace(microsecond=0),
        )

        order_obj_buy = {
            "instrument_token": order_response.instrument_token,
            "product": order_response.product.value,
            "quantity": order_response.quantity,
            "transaction_type": order_response.transaction_type.value,
            "price": order_response.average_price
        }
        charges_on_order = calculate_brokerage(order_obj=order_obj_buy)

        if charges_on_order["success"] == True:
            order.total_charges=charges_on_order["data"]["charges"]["total"]

        if order_response.transaction_type.value == TransactionType.BUY:
            new_position = Position(
                trading_symbol = order_response.instrument_token,
                buy_price=order_response.average_price,
                buy_timestamp = order_response.order_timestamp,
                qty_bought = order_response.filled_quantity,
                buy_order_id = order_id,
                trigger_price = placed_order_obj['trigger_price'],
            )
        else:
            new_position = Position(
                trading_symbol=order_response.instrument_token,
                sell_price=order_response.average_price,
                sell_timestamp = order_response.order_timestamp,
                qty_sold = order_response.filled_quantity,
                Sell_order_id = order_id,
                trigger_price = placed_order_obj['trigger_price'],
            )


        # Creating position
        # new_position:Position = Position(
        #     "trading_symbol"="",
        #     "buy_order_id"="",
        #     "sell_order_id"="",
        #     "qty_bought"=qty_bought,
        #     "qty_sold"=qty_sold,
        #     "buy_price"= buy_price,
        #     "sell_price"=sell_price,
        #     "buy_timestamp"=buy_timestamp,
        #     "sell_timestamp"=sell_timestamp
        # )

        with orm_session() as session:
            session.add(order)
            fancy_print(msg=f"Details for order id :{order_id} updated successfully", border_color="green",
                        title="Order Detail Updated")
            session.add(new_position)
            fancy_print(msg=f"Position created OR updated for :{order_id}  successfully", border_color="green",
                        title="POSITION CREATED OR UPDATED")
            session.commit()

    except HTTPError as http_err:
        fancy_print(str(http_err), border_color="red", title="Order canceled Failed -Http Error")
    except Exception as err:
        fancy_print(str(err), border_color="red", title="Order Details Failed -- Unknown Error")
        print_json(data=headers)
        return False
