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
            broker_mode: 券商模式 ("gjzj" | "futu" | "auto")

        Returns:
            BaseBroker 实例
        """
        from brokers.base_broker import BaseBroker

        # 获取券商模式
        if broker_mode is None:
            broker_mode = get_config_value("BROKER_MODE", None)

        if not broker_mode:
             raise ValueError("BROKER_MODE not specified in config or arguments")

        # 如果是 auto 模式，根据 symbol 自动选择
        if broker_mode == "auto":
            if symbol:
                market = BrokerAdapterFactory.detect_market(symbol)
                if market == "cn":
                    broker_mode = "gjzj"
                else:
                    broker_mode = "futu"
            else:
                # 如果没有 symbol，抛出异常
                raise ValueError("Cannot auto-detect broker mode without symbol")

        # 根据模式创建适配器
        if broker_mode == "gjzj":
            from brokers.gjzj.gjzj_adapter import GjzjAdapter
            return GjzjAdapter.create_from_config()

        elif broker_mode == "futu":
            from brokers.futu.futu_adapter import FutuAdapter
            return FutuAdapter.create_from_config()

        else:
            raise ValueError(f"Unknown or unsupported broker mode: {broker_mode}")

    @staticmethod
    def get_broker_config(broker_type: str) -> Dict[str, Any]:
        """
        获取券商配置
        所有配置项都从 .env 文件中的环境变量读取

        Args:
            broker_type: 券商类型 ("gjzj" | "futu")

        Returns:
            配置字典

        配置项说明：
        - Gjzj适配器:
          - GJZJ_ACCOUNT_ID: 账户ID（默认: "default"）
          - GJZJ_SESSION_ID: 会话ID，0表示默认会话（默认: "0"）
          - GJZJ_STRATEGY_NAME: 策略名称（默认: "AI-Trader"）
          - GJZJ_PATH: MiniQMT客户端userdata_mini的完整路径（必需）

        - Futu适配器:
          - FUTU_ACCOUNT_ID: 账户ID（默认: "default"）
          - FUTU_HOST: Futu API主机地址（默认: "127.0.0.1"）
          - FUTU_PORT: Futu API端口（默认: "11111"）
          - FUTU_MARKET: 市场类型（默认: "US"）
          - FUTU_SECURITY_FIRM: 券商名称（默认: ""）
          - FUTU_REAL_TRADE: 是否真实交易，"true"或"false"（默认: "false"）
        """
        config = {
            "account_id": get_config_value(f"{broker_type.upper()}_ACCOUNT_ID", "default")
        }

        if broker_type == "gjzj":
            config.update({
                "account_id": get_config_value("GJZJ_ACCOUNT_ID", "default"),
                "session_id": int(get_config_value("GJZJ_SESSION_ID", "0")),  # 会话ID，0表示默认会话
                "strategy_name": get_config_value("GJZJ_STRATEGY_NAME", "AI-Trader"),  # 策略名称
                "path": get_config_value("GJZJ_PATH", None),  # MiniQMT客户端userdata_mini路径
                # trader实例需要在运行时创建，不能从环境变量获取
            })
        elif broker_type == "futu":
            config.update({
                "host": get_config_value("FUTU_HOST", "127.0.0.1"),
                "port": int(get_config_value("FUTU_PORT", "11111")),
                "market": get_config_value("FUTU_MARKET", "US"),
                "security_firm": get_config_value("FUTU_SECURITY_FIRM", ""),
            })

        return config
