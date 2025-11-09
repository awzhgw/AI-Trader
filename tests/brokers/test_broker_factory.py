"""
BrokerAdapterFactory单测
"""
import os
import pytest
from unittest.mock import patch
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)

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
        # 从 .env 读取 BROKER_MODE，如果没有则使用默认值
        broker_mode = os.getenv("BROKER_MODE", "mock")
        mock_get_config.side_effect = lambda key, default=None: {
            "BROKER_MODE": broker_mode,
            "SIGNATURE": os.getenv("SIGNATURE", "test_signature")
        }.get(key, default)

        broker = BrokerAdapterFactory.create_broker(broker_mode="mock")
        assert broker.broker_type == "mock"

    @patch('brokers.broker_factory.get_config_value')
    def test_get_broker_config(self, mock_get_config):
        """测试获取券商配置"""
        # 从 .env 读取配置，如果没有则使用默认值
        mock_get_config.side_effect = lambda key, default=None: {
            "GJZJ_ACCOUNT_ID": os.getenv("GJZJ_ACCOUNT_ID", "gjzj_account"),
            "GJZJ_SESSION_ID": os.getenv("GJZJ_SESSION_ID", "0"),
            "FUTU_ACCOUNT_ID": os.getenv("FUTU_ACCOUNT_ID", "futu_account"),
            "FUTU_HOST": os.getenv("FUTU_HOST", "127.0.0.1"),
            "FUTU_PORT": os.getenv("FUTU_PORT", "11111"),
            "FUTU_MARKET": os.getenv("FUTU_MARKET", "US"),
            "FUTU_SECURITY_FIRM": os.getenv("FUTU_SECURITY_FIRM", "futu_firm"),
            "FUTU_REAL_TRADE": os.getenv("FUTU_REAL_TRADE", "false")
        }.get(key, default)

        gjzj_config = BrokerAdapterFactory.get_broker_config("gjzj")
        expected_account_id = os.getenv("GJZJ_ACCOUNT_ID", "gjzj_account")
        expected_session_id = int(os.getenv("GJZJ_SESSION_ID", "0"))
        assert gjzj_config["account_id"] == expected_account_id
        assert gjzj_config["session_id"] == expected_session_id

        futu_config = BrokerAdapterFactory.get_broker_config("futu")
        expected_futu_account = os.getenv("FUTU_ACCOUNT_ID", "futu_account")
        expected_futu_host = os.getenv("FUTU_HOST", "127.0.0.1")
        expected_futu_port = int(os.getenv("FUTU_PORT", "11111"))
        assert futu_config["account_id"] == expected_futu_account
        assert futu_config["host"] == expected_futu_host
        assert futu_config["port"] == expected_futu_port
