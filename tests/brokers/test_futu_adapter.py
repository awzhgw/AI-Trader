"""
FutuAdapter单测
"""
import pytest
from unittest.mock import patch, MagicMock

from brokers.futu.futu_adapter import FutuAdapter
from brokers.base_broker import OrderType


class TestFutuAdapter:
    """FutuAdapter测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.config = {
            "account_id": "test_account",
            "host": "127.0.0.1",
            "port": 11111,
            "market": "US",
            "security_firm": "test_firm",
            "real_trade": False
        }

    @patch('brokers.futu.futu_adapter.get_config_value')
    def test_init(self, mock_get_config):
        """测试初始化"""
        mock_get_config.return_value = "2025-01-15"

        adapter = FutuAdapter(self.config)
        assert adapter.broker_type == "futu"
        assert adapter.host == "127.0.0.1"
        assert adapter.port == 11111

    @patch('brokers.futu.futu_adapter.get_config_value')
    def test_connect(self, mock_get_config):
        """测试连接"""
        mock_get_config.return_value = "2025-01-15"

        adapter = FutuAdapter(self.config)
        result = adapter.connect()
        # 由于是模拟实现，应该返回True
        assert result is True

    @patch('brokers.futu.futu_adapter.get_config_value')
    @patch('brokers.futu.futu_adapter.get_open_prices')
    def test_get_price(self, mock_get_prices, mock_get_config):
        """测试获取价格"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"AAPL_price": 150.0}

        adapter = FutuAdapter(self.config)
        price = adapter.get_price("AAPL")
        assert price == 150.0

    @patch('brokers.futu.futu_adapter.get_config_value')
    @patch('brokers.futu.futu_adapter.get_open_prices')
    def test_buy_success(self, mock_get_prices, mock_get_config):
        """测试买入成功"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"AAPL_price": 150.0}

        adapter = FutuAdapter(self.config)
        result = adapter.buy("AAPL", 10)

        assert result["success"] is True
        assert result["symbol"] == "AAPL"
        assert result["amount"] == 10

    @patch('brokers.futu.futu_adapter.get_config_value')
    @patch('brokers.futu.futu_adapter.get_open_prices')
    def test_sell_protect_manual_position(self, mock_get_prices, mock_get_config):
        """测试卖出保护人工持仓"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"AAPL_price": 150.0}

        adapter = FutuAdapter(self.config)

        # AI买入10股
        adapter.buy("AAPL", 10)

        # 尝试卖出20股（应该失败，因为AI只有10股）
        result = adapter.sell("AAPL", 20)

        assert result["success"] is False
        assert "AI持仓不足" in result["error"]
