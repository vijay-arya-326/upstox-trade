import time
from typing import Optional
from core.config.settings import init_settings, headers_fun, prepare_headers
from core.market import download_nse_file
from core.auth import check_user_auth, validate_sandbox_token
from core.persistence.db import db_session
from core.logging.fancy import fancy_print
from strategy.base import Strategy
from core.persistence.models import Position, OrderDetail
from core.config.constants import SANDBOX_ENV_NAME


def _get_settings():
    from core.config.settings import (
        APPNAME, LOADED_ENV, INSTRUMENT_KEY, STOP_LOSS_PERCENTAGE,
        STOP_LOSS_DIFFERENCE_BEFORE_UPDATE, UPSTOX_API_URL,
        UPSTOX_HF_API_URL, SANDBOX_UPSTOX_URL, ORDER_RETRY_COUNT,
        SEGMENT, SEGMENT_OF_INDEX, UNDERLYING_SYMBOL, UNDERLYING_SYMBOL_OF_INDEX,
        EXPIRY_DATE, DB_PATH_FULL, ENV_PATH, SANDBOX_ACCESS_TOKEN,
        UPSTOX_CLIENT_ID, UPSTOX_CLIENT_SECRET, ACCESS_TOKEN,
        UPSTOX_REDIRECT_URI, UPSTOX_ACCESS_TOKEN,
    )
    return {
        "APPNAME": APPNAME,
        "LOADED_ENV": LOADED_ENV,
        "INSTRUMENT_KEY": INSTRUMENT_KEY,
        "STOP_LOSS_PERCENTAGE": STOP_LOSS_PERCENTAGE,
        "STOP_LOSS_DIFFERENCE_BEFORE_UPDATE": STOP_LOSS_DIFFERENCE_BEFORE_UPDATE,
        "UPSTOX_API_URL": UPSTOX_API_URL,
        "UPSTOX_HF_API_URL": UPSTOX_HF_API_URL,
        "SANDBOX_UPSTOX_URL": SANDBOX_UPSTOX_URL,
        "ORDER_RETRY_COUNT": ORDER_RETRY_COUNT,
        "SEGMENT": SEGMENT,
        "SEGMENT_OF_INDEX": SEGMENT_OF_INDEX,
        "UNDERLYING_SYMBOL": UNDERLYING_SYMBOL,
        "UNDERLYING_SYMBOL_OF_INDEX": UNDERLYING_SYMBOL_OF_INDEX,
        "EXPIRY_DATE": EXPIRY_DATE,
        "DB_PATH_FULL": DB_PATH_FULL,
        "ENV_PATH": ENV_PATH,
        "SANDBOX_ACCESS_TOKEN": SANDBOX_ACCESS_TOKEN,
        "UPSTOX_CLIENT_ID": UPSTOX_CLIENT_ID,
        "UPSTOX_CLIENT_SECRET": UPSTOX_CLIENT_SECRET,
        "ACCESS_TOKEN": ACCESS_TOKEN,
        "UPSTOX_REDIRECT_URI": UPSTOX_REDIRECT_URI,
        "UPSTOX_ACCESS_TOKEN": UPSTOX_ACCESS_TOKEN,
    }


class  :
    def __init__(self, strategy: Strategy, instrument_key: str = None):
        self.strategy = strategy
        self.instrument_key = instrument_key
        self.position: Optional[Position] = None
        self.pending_order_id: Optional[str] = None

    def run(self):
        s = _get_settings()
        fancy_print(s["APPNAME"], border_color="green")
        download_nse_file()
        check_user_auth()
        if s["LOADED_ENV"] in SANDBOX_ENV_NAME:
            if not validate_sandbox_token():
                import sys
                sys.exit(1)

        with db_session() as session:
            session.execute("Select 1;")
            fancy_print(msg="DB Connected", title="DB Connected", border_color="green")

        fancy_print(f"Starting strategy engine for {self.instrument_key or s['INSTRUMENT_KEY']}", border_color="cyan")

        while True:
            try:
                from core.market import getMarketData
                ltp_response = getMarketData(instrument_token=self.instrument_key or s["INSTRUMENT_KEY"])
                
                if self.position is None:
                    signal = self.strategy.on_tick(ltp_response, None)
                    if signal.action:
                        self._place_entry_order(signal)
                else:
                    result = self.strategy.on_tick(ltp_response, self.position)
                    if result.exit_signal:
                        self._close_position()
                    elif result.new_sl:
                        self._update_sl(result.new_sl)
                        
            except KeyboardInterrupt:
                fancy_print("Shutting down...", border_color="yellow")
                break
            except Exception as e:
                fancy_print(f"Error in strategy loop: {e}", border_color="red")
            
            time.sleep(1)

    def _place_entry_order(self, signal):
        from core.orders import place_order
        from core.orders.models import OrderDTOModel
        
        s = _get_settings()
        ik = self.instrument_key or s["INSTRUMENT_KEY"]
        
        order_obj = OrderDTOModel(
            quantity=75,
            product="D",
            validity="DAY",
            price=0,
            tag=f"{self.strategy.__class__.__name__}-entry",
            instrument_token=ik,
            order_type="SL-M",
            transaction_type=signal.action.value,
            disclosed_quantity=0,
            trigger_price=signal.initial_sl or 0,
            is_amo=False,
            slice=True,
        )
        
        place_order(market_price=signal.entry_price, order_obj=order_obj)

    def _update_sl(self, new_sl: float):
        from core.orders import update_sl_for
        if self.position and self.position.buy_order_id:
            update_sl_for(order_id=self.position.buy_order_id, new_market_price=new_sl)

    def _close_position(self):
        from core.orders import cancel_order, place_order
        from core.orders.models import OrderDTOModel
        from core.utils.enums import TransactionType
        
        if self.position and self.position.buy_order_id:
            cancel_order(self.position.buy_order_id)
        
        exit_type = TransactionType.SELL if self.position.qty_bought > 0 else TransactionType.BUY
        s = _get_settings()
        ik = self.instrument_key or s["INSTRUMENT_KEY"]
        
        order_obj = OrderDTOModel(
            quantity=self.position.qty_bought or self.position.qty_sold,
            product="D",
            validity="DAY",
            price=0,
            tag=f"{self.strategy.__class__.__name__}-exit",
            instrument_token=ik,
            order_type="MARKET",
            transaction_type=exit_type.value,
            disclosed_quantity=0,
            trigger_price=0,
            is_amo=False,
            slice=True,
        )
        place_order(market_price=0, order_obj=order_obj)
        self.position = None