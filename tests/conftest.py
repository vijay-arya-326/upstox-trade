import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from core.config.settings import init_settings


@pytest.fixture(scope="session", autouse=True)
def init_test_env():
    init_settings("demo")


@pytest.fixture
def mock_ltp():
    return 25000.0


@pytest.fixture
def mock_position():
    from core.persistence.models import Position
    from core.utils.enums import PositionStatus
    from datetime import datetime
    
    return Position(
        id=1,
        trading_symbol="NSE_FO|NIFTY25SEP25000CE",
        qty_bought=75,
        qty_sold=0,
        buy_order_id=1001,
        buy_price=24900.0,
        sell_price=None,
        trigger_price=24650.0,
        buy_timestamp=datetime.now(),
        sell_timestamp=None,
        status=PositionStatus.OPEN,
    )