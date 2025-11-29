"""
BrokerAdapterFactory单测
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from brokers.broker_factory import BrokerAdapterFactory

class TestBrokerAdapterFactory:
    """BrokerAdapterFactory测试类"""
    
    @pytest.mark.parametrize("symbol, expected", [
        ("600519.SH", "cn"),
        ("000001.SZ", "cn"),
        ("AAPL", "us"),
        ("MSFT", "us"),
        ("00700", "us"),
    ])
    def test_detect_market(self, symbol, expected):
        """测试识别市场"""
        assert BrokerAdapterFactory.detect_market(symbol) == expected

    def test_get_broker_config(self):
        """测试获取券商配置"""
        gjzj_config = BrokerAdapterFactory.get_broker_config("gjzj")
        assert gjzj_config["account_id"] == os.getenv("GJZJ_ACCOUNT_ID", "default")
        
        futu_config = BrokerAdapterFactory.get_broker_config("futu")
        assert futu_config["account_id"] == os.getenv("FUTU_ACCOUNT_ID", "default")

    @patch("brokers.gjzj.gjzj_adapter.GjzjAdapter")
    def test_create_broker_gjzj(self, mock_cls):
        """测试创建GJZJ适配器"""
        mock_instance = mock_cls.create_from_config.return_value
        
        broker = BrokerAdapterFactory.create_broker(broker_mode="gjzj")
        
        assert broker == mock_instance
        mock_cls.create_from_config.assert_called_once()

    @patch("brokers.futu.futu_adapter.FutuAdapter")
    def test_create_broker_futu(self, mock_cls):
        """测试创建Futu适配器"""
        mock_instance = mock_cls.create_from_config.return_value
        
        broker = BrokerAdapterFactory.create_broker(broker_mode="futu")
        
        assert broker == mock_instance
        mock_cls.create_from_config.assert_called_once()

    def test_create_broker_invalid(self):
        """测试无效的broker模式"""
        with pytest.raises(ValueError, match="Unknown or unsupported broker mode"):
            BrokerAdapterFactory.create_broker(broker_mode="invalid_mode")

    @pytest.mark.parametrize("symbol, mode, patch_target", [
        ("600519.SH", "cn", "brokers.gjzj.gjzj_adapter.GjzjAdapter"),
        ("AAPL", "us", "brokers.futu.futu_adapter.FutuAdapter"),
    ])
    def test_create_broker_auto(self, symbol, mode, patch_target):
        """测试自动模式"""
        with patch(patch_target) as mock_cls:
            mock_instance = mock_cls.create_from_config.return_value
            
            broker = BrokerAdapterFactory.create_broker(symbol=symbol, broker_mode="auto")
            
            assert broker == mock_instance
            mock_cls.create_from_config.assert_called_once()
