"""
MockAdapter单测
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from brokers.mock.mock_adapter import MockAdapter
from brokers.base_broker import OrderType


class TestMockAdapter:
    """MockAdapter测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        # 设置环境变量
        os.environ["SIGNATURE"] = "test_signature"
        os.environ["TODAY_DATE"] = "2025-01-15"
        os.environ["LOG_PATH"] = "./data/agent_data"

        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {"account_id": "test_account"}

    def teardown_method(self):
        """每个测试方法后执行"""
        # 清理环境变量
        os.environ.pop("SIGNATURE", None)
        os.environ.pop("TODAY_DATE", None)
        os.environ.pop("LOG_PATH", None)

        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('brokers.mock.mock_adapter.get_config_value')
    @patch('brokers.mock.mock_adapter.get_open_prices')
    @patch('brokers.mock.mock_adapter.get_latest_position')
    def test_buy_success(self, mock_get_position, mock_get_prices, mock_get_config):
        """测试买入成功"""
        # Mock配置
        mock_get_config.side_effect = lambda key, default=None: {
            "SIGNATURE": "test_signature",
            "TODAY_DATE": "2025-01-15",
            "LOG_PATH": "./data/agent_data"
        }.get(key, default)

        # Mock价格
        mock_get_prices.return_value = {"AAPL_price": 150.0}

        # Mock持仓（初始有10000现金）
        mock_get_position.return_value = ({"CASH": 10000.0}, 0)

        adapter = MockAdapter(self.test_config)
        result = adapter.buy("AAPL", 10)

        assert result["success"] is True
        assert result["symbol"] == "AAPL"
        assert result["amount"] == 10
        assert result["price"] == 150.0

    @patch('brokers.mock.mock_adapter.get_config_value')
    @patch('brokers.mock.mock_adapter.get_open_prices')
    @patch('brokers.mock.mock_adapter.get_latest_position')
    def test_buy_insufficient_cash(self, mock_get_position, mock_get_prices, mock_get_config):
        """测试买入失败（现金不足）"""
        mock_get_config.side_effect = lambda key, default=None: {
            "SIGNATURE": "test_signature",
            "TODAY_DATE": "2025-01-15",
            "LOG_PATH": "./data/agent_data"
        }.get(key, default)

        mock_get_prices.return_value = {"AAPL_price": 150.0}
        mock_get_position.return_value = ({"CASH": 100.0}, 0)  # 现金不足

        adapter = MockAdapter(self.test_config)
        result = adapter.buy("AAPL", 10)

        assert result["success"] is False
        assert "Insufficient cash" in result["error"]

    @patch('brokers.mock.mock_adapter.get_config_value')
    @patch('brokers.mock.mock_adapter.get_open_prices')
    @patch('brokers.mock.mock_adapter.get_latest_position')
    def test_sell_success(self, mock_get_position, mock_get_prices, mock_get_config):
        """测试卖出成功"""
        mock_get_config.side_effect = lambda key, default=None: {
            "SIGNATURE": "test_signature",
            "TODAY_DATE": "2025-01-15",
            "LOG_PATH": "./data/agent_data"
        }.get(key, default)

        mock_get_prices.return_value = {"AAPL_price": 160.0}
        # 初始持仓：AAPL 10股，现金10000
        mock_get_position.return_value = ({"AAPL": 10, "CASH": 10000.0}, 0)

        adapter = MockAdapter(self.test_config)

        # 先买入，建立AI持仓
        adapter.buy("AAPL", 10)

        # 然后卖出
        result = adapter.sell("AAPL", 5)

        assert result["success"] is True
        assert result["symbol"] == "AAPL"
        assert result["amount"] == 5

    @patch('brokers.mock.mock_adapter.get_config_value')
    @patch('brokers.mock.mock_adapter.get_open_prices')
    @patch('brokers.mock.mock_adapter.get_latest_position')
    def test_sell_protect_manual_position(self, mock_get_position, mock_get_prices, mock_get_config):
        """测试卖出保护人工持仓"""
        mock_get_config.side_effect = lambda key, default=None: {
            "SIGNATURE": "test_signature",
            "TODAY_DATE": "2025-01-15",
            "LOG_PATH": "./data/agent_data"
        }.get(key, default)

        mock_get_prices.return_value = {"AAPL_price": 160.0}
        # 总持仓10股（其中5股是AI买入的，5股是人工持仓）
        mock_get_position.return_value = ({"AAPL": 10, "CASH": 10000.0}, 0)

        adapter = MockAdapter(self.test_config)

        # AI只买入5股
        adapter.buy("AAPL", 5)

        # 尝试卖出10股（应该失败，因为AI只有5股）
        result = adapter.sell("AAPL", 10)

        assert result["success"] is False
        assert "AI持仓不足" in result["error"]
        assert result["ai_position"] == 5
        assert result["total_position"] == 10

    @patch('brokers.mock.mock_adapter.get_config_value')
    @patch('brokers.mock.mock_adapter.get_open_prices')
    @patch('brokers.mock.mock_adapter.get_latest_position')
    def test_get_position(self, mock_get_position, mock_get_prices, mock_get_config):
        """测试获取持仓"""
        mock_get_config.side_effect = lambda key, default=None: {
            "SIGNATURE": "test_signature",
            "TODAY_DATE": "2025-01-15",
            "LOG_PATH": "./data/agent_data"
        }.get(key, default)

        mock_get_prices.return_value = {"AAPL_price": 150.0, "MSFT_price": 300.0}
        # 总持仓：AAPL 10股（AI买入5股），MSFT 5股（全部是人工持仓）
        mock_get_position.return_value = ({"AAPL": 10, "MSFT": 5, "CASH": 10000.0}, 0)

        adapter = MockAdapter(self.test_config)

        # AI买入AAPL 5股
        adapter.buy("AAPL", 5)

        # 获取持仓
        position = adapter.get_position()

        assert "total_positions" in position
        assert "ai_positions" in position
        assert "manual_positions" in position
        assert position["total_positions"]["AAPL"] == 10
        assert position["ai_positions"]["AAPL"] == 5
        assert position["manual_positions"]["AAPL"] == 5
        assert position["manual_positions"]["MSFT"] == 5

    @patch('brokers.mock.mock_adapter.get_config_value')
    def test_cn_stock_lot_size(self, mock_get_config):
        """测试A股必须100的倍数"""
        mock_get_config.side_effect = lambda key, default=None: {
            "SIGNATURE": "test_signature",
            "TODAY_DATE": "2025-01-15",
            "LOG_PATH": "./data/agent_data"
        }.get(key, default)

        adapter = MockAdapter(self.test_config)

        # 尝试买入非100倍数的A股
        result = adapter.buy("600519.SH", 50)

        assert result["success"] is False
        assert "multiples of 100" in result["error"]
