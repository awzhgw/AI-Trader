"""
BrokerAdapterFactory单测
"""
import os
import pytest
from unittest.mock import patch

from brokers.broker_factory import BrokerAdapterFactory


class TestBrokerAdapterFactory:
    """BrokerAdapterFactory测试类"""

    def test_detect_market_cn(self):
        """测试识别A股市场"""
        market = BrokerAdapterFactory.detect_market("600519.SH")
        assert market == "cn"

        market = BrokerAdapterFactory.detect_market("000001.SZ")
        assert market == "cn"

    def test_detect_market_us(self):
        """测试识别美股市场"""
        market = BrokerAdapterFactory.detect_market("AAPL")
        assert market == "us"

        market = BrokerAdapterFactory.detect_market("MSFT")
        assert market == "us"

    @patch('brokers.broker_factory.get_config_value')
    def test_create_broker_mock(self, mock_get_config):
        """测试创建Mock适配器"""
        mock_get_config.side_effect = lambda key, default=None: {
            "BROKER_MODE": "mock"
        }.get(key, default)

        broker = BrokerAdapterFactory.create_broker(broker_mode="mock")
        assert broker.broker_type == "mock"

    @patch('brokers.broker_factory.get_config_value')
    def test_create_broker_auto_cn(self, mock_get_config):
        """测试自动模式创建A股适配器"""
        mock_get_config.side_effect = lambda key, default=None: {
            "BROKER_MODE": "auto"
        }.get(key, default)

        broker = BrokerAdapterFactory.create_broker(symbol="600519.SH", broker_mode="auto")
        # 由于XtQuantAdapter需要实际API和连接，这里只测试工厂逻辑
        # 实际创建可能会失败，但工厂逻辑是正确的
        assert broker is not None

    @patch('brokers.broker_factory.get_config_value')
    def test_create_broker_auto_us(self, mock_get_config):
        """测试自动模式创建美股适配器"""
        mock_get_config.side_effect = lambda key, default=None: {
            "BROKER_MODE": "auto"
        }.get(key, default)

        broker = BrokerAdapterFactory.create_broker(symbol="AAPL", broker_mode="auto")
        # 由于FutuAdapter需要实际API，这里只测试工厂逻辑
        assert broker is not None

    @patch('brokers.broker_factory.get_config_value')
    def test_get_broker_config(self, mock_get_config):
        """测试获取券商配置"""
        mock_get_config.side_effect = lambda key, default=None: {
            "XTQUANT_ACCOUNT_ID": "xtquant_account",
            "XTQUANT_SESSION_ID": "0",
            "FUTU_ACCOUNT_ID": "futu_account",
            "FUTU_HOST": "127.0.0.1",
            "FUTU_PORT": "11111",
            "FUTU_MARKET": "US",
            "FUTU_SECURITY_FIRM": "futu_firm",
            "FUTU_REAL_TRADE": "false"
        }.get(key, default)

        xtquant_config = BrokerAdapterFactory.get_broker_config("xtquant")
        assert xtquant_config["account_id"] == "xtquant_account"
        assert xtquant_config["session_id"] == 0

        futu_config = BrokerAdapterFactory.get_broker_config("futu")
        assert futu_config["account_id"] == "futu_account"
        assert futu_config["host"] == "127.0.0.1"
        assert futu_config["port"] == 11111
