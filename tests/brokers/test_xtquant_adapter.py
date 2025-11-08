"""
XtQuantAdapter单测
"""
import pytest
from unittest.mock import patch, MagicMock

from brokers.xtquant.xtquant_adapter import XtQuantAdapter
from brokers.base_broker import OrderType


class TestXtQuantAdapter:
    """XtQuantAdapter测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.config = {
            "account_id": "test_account",
            "session_id": 0
        }

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    def test_init(self, mock_get_config):
        """测试初始化"""
        mock_get_config.return_value = "2025-01-15"

        adapter = XtQuantAdapter(self.config)
        assert adapter.broker_type == "xtquant"
        assert adapter.account_id == "test_account"
        assert adapter.session_id == 0

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    @patch('brokers.xtquant.xtquant_adapter.xttrader')
    def test_connect_success(self, mock_xttrader, mock_get_config):
        """测试连接成功"""
        mock_get_config.return_value = "2025-01-15"

        # Mock XtQuantTrader
        mock_trader_instance = MagicMock()
        mock_trader_instance.start.return_value = 1  # session_id > 0表示成功
        mock_xttrader.XtQuantTrader.return_value = mock_trader_instance

        adapter = XtQuantAdapter(self.config)
        result = adapter.connect()

        assert result is True
        assert adapter._connected is True
        assert adapter.trader is not None

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    def test_connect_import_error(self, mock_get_config):
        """测试连接失败（模块未安装）"""
        mock_get_config.return_value = "2025-01-15"

        # 模拟ImportError
        import sys
        original_import = __builtins__.__import__
        def mock_import(name, *args, **kwargs):
            if name == 'xtquant':
                raise ImportError("No module named 'xtquant'")
            return original_import(name, *args, **kwargs)

        adapter = XtQuantAdapter(self.config)
        result = adapter.connect()

        assert result is False

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    @patch('brokers.xtquant.xtquant_adapter.get_open_prices')
    def test_get_price(self, mock_get_prices, mock_get_config):
        """测试获取价格"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"600519.SH_price": 1800.0}

        adapter = XtQuantAdapter(self.config)
        price = adapter.get_price("600519.SH")
        assert price == 1800.0

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    def test_buy_cn_lot_size(self, mock_get_config):
        """测试A股买入必须100的倍数"""
        mock_get_config.return_value = "2025-01-15"

        adapter = XtQuantAdapter(self.config)
        result = adapter.buy("600519.SH", 50)  # 不是100的倍数

        assert result["success"] is False
        assert "multiples of 100" in result["error"]

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    def test_buy_not_connected(self, mock_get_config):
        """测试买入失败（未连接）"""
        mock_get_config.return_value = "2025-01-15"

        adapter = XtQuantAdapter(self.config)
        result = adapter.buy("600519.SH", 100)

        assert result["success"] is False
        assert "未连接" in result["error"]

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    @patch('brokers.xtquant.xtquant_adapter.get_open_prices')
    @patch('brokers.xtquant.xtquant_adapter.xttrader')
    def test_buy_success(self, mock_xttrader, mock_get_prices, mock_get_config):
        """测试买入成功"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"600519.SH_price": 1800.0}

        # Mock XtQuantTrader
        mock_trader_instance = MagicMock()
        mock_trader_instance.start.return_value = 1
        mock_trader_instance.order_stock.return_value = 12345  # order_id
        mock_trader_instance.query_stock_positions.return_value = []
        mock_xttrader.XtQuantTrader.return_value = mock_trader_instance

        adapter = XtQuantAdapter(self.config)
        adapter.connect()
        result = adapter.buy("600519.SH", 100)

        assert result["success"] is True
        assert result["symbol"] == "600519.SH"
        assert result["amount"] == 100

    @patch('brokers.xtquant.xtquant_adapter.get_config_value')
    @patch('brokers.xtquant.xtquant_adapter.get_open_prices')
    @patch('brokers.xtquant.xtquant_adapter.xttrader')
    def test_sell_protect_manual_position(self, mock_xttrader, mock_get_prices, mock_get_config):
        """测试卖出保护人工持仓"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"600519.SH_price": 1800.0}

        # Mock XtQuantTrader
        mock_trader_instance = MagicMock()
        mock_trader_instance.start.return_value = 1
        mock_trader_instance.order_stock.return_value = 12345
        mock_trader_instance.query_stock_positions.return_value = []
        mock_xttrader.XtQuantTrader.return_value = mock_trader_instance

        adapter = XtQuantAdapter(self.config)
        adapter.connect()

        # AI买入100股
        adapter.buy("600519.SH", 100)

        # 尝试卖出200股（应该失败，因为AI只有100股）
        result = adapter.sell("600519.SH", 200)

        assert result["success"] is False
        assert "AI持仓不足" in result["error"]
