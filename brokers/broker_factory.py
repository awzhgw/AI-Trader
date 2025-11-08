"""
券商适配器工厂
根据环境变量和市场类型创建对应的适配器
"""
from typing import Optional, Dict, Any
from tools.general_tools import get_config_value


class BrokerAdapterFactory:
    """券商适配器工厂"""

    @staticmethod
    def detect_market(symbol: str) -> str:
        """
        根据股票代码自动识别市场

        Args:
            symbol: 股票代码

        Returns:
            "cn" (A股) 或 "us" (美股)
        """
        if symbol.endswith((".SH", ".SZ")):
            return "cn"
        return "us"

    @staticmethod
    def create_broker(
        symbol: Optional[str] = None,
        broker_mode: Optional[str] = None
    ) -> 'BaseBroker':
        """
        创建券商适配器

        Args:
            symbol: 股票代码（用于自动识别市场）
            broker_mode: 券商模式 ("mock" | "xtquant" | "futu" | "auto")

        Returns:
            BaseBroker 实例
        """
        from brokers.base_broker import BaseBroker

        # 获取券商模式
        if broker_mode is None:
            broker_mode = get_config_value("BROKER_MODE", "mock")

        # 如果是 auto 模式，根据 symbol 自动选择
        if broker_mode == "auto":
            if symbol:
                market = BrokerAdapterFactory.detect_market(symbol)
                if market == "cn":
                    broker_mode = "xtquant"
                else:
                    broker_mode = "futu"
            else:
                # 如果没有 symbol，默认使用 mock
                broker_mode = "mock"

        # 根据模式创建适配器
        if broker_mode == "mock":
            from brokers.mock.mock_adapter import MockAdapter
            return MockAdapter.create_from_config()

        elif broker_mode == "xtquant":
            from brokers.xtquant.xtquant_adapter import XtQuantAdapter
            return XtQuantAdapter.create_from_config()

        elif broker_mode == "futu":
            from brokers.futu.futu_adapter import FutuAdapter
            return FutuAdapter.create_from_config()

        else:
            raise ValueError(f"Unknown broker mode: {broker_mode}")

    @staticmethod
    def get_broker_config(broker_type: str) -> Dict[str, Any]:
        """
        获取券商配置

        Args:
            broker_type: 券商类型

        Returns:
            配置字典
        """
        config = {
            "account_id": get_config_value(f"{broker_type.upper()}_ACCOUNT_ID", "default")
        }

        if broker_type == "xtquant":
            config.update({
                "session_id": int(get_config_value("XTQUANT_SESSION_ID", "0")),  # 会话ID，0表示默认会话
                # trader实例需要在运行时创建，不能从环境变量获取
            })
        elif broker_type == "futu":
            config.update({
                "host": get_config_value("FUTU_HOST", "127.0.0.1"),
                "port": int(get_config_value("FUTU_PORT", "11111")),
                "market": get_config_value("FUTU_MARKET", "US"),
                "security_firm": get_config_value("FUTU_SECURITY_FIRM", ""),
                "real_trade": get_config_value("FUTU_REAL_TRADE", "false").lower() == "true",
            })

        return config
