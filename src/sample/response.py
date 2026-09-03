import json

order_detail_sample_response = json.loads('''{
  "status": "success",
  "data": {
    "exchange": "NSE",
    "product": "D",
    "price": 571.0,
    "quantity": 1,
    "status": "complete",
    "tag": null,
    "instrument_token": "NSE_EQ|INE062A01020",
    "placed_by": "******",
    "trading_symbol": "SBIN-EQ",
    "tradingsymbol": "SBIN-EQ",
    "order_type": "LIMIT",
    "validity": "DAY",
    "trigger_price": 0.0,
    "disclosed_quantity": 0,
    "transaction_type": "BUY",
    "average_price": 570.95,
    "filled_quantity": 1,
    "pending_quantity": 0,
    "status_message": null,
    "status_message_raw": null,
    "exchange_order_id": "1300000025660919",
    "parent_order_id": null,
    "order_id": "231019025562880",
    "variety": "SIMPLE",
    "order_timestamp": "2023-10-19 13:25:13",
    "exchange_timestamp": "2023-10-19 13:25:13",
    "is_amo": false,
    "order_request_id": "1",
    "order_ref_id": "GTT-C23191000044253"
  }
}''')