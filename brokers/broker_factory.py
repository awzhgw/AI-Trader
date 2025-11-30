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
        """根据股票代码自动识别市场"""
        return "cn" if symbol.endswith((".SH", ".SZ")) else "us"

    @staticmethod
    def create_broker(symbol: Optional[str] = None, broker_mode: Optional[str] = None) -> 'BaseBroker':
        """创建券商适配器"""
        if broker_mode is None:
            broker_mode = get_config_value("BROKER_MODE")
        
        if not broker_mode:
            raise ValueError("BROKER_MODE not specified")

        if broker_mode == "auto":
            if not symbol:
                raise ValueError("Cannot auto-detect broker mode without symbol")
            broker_mode = "gjzj" if BrokerAdapterFactory.detect_market(symbol) == "cn" else "futu"

        if broker_mode == "gjzj":
            from brokers.gjzj.gjzj_adapter import GjzjAdapter
            return GjzjAdapter.create_from_config()
        elif broker_mode == "futu":
            from brokers.futu.futu_adapter import FutuAdapter
            return FutuAdapter.create_from_config()
        else:
            raise ValueError(f"Unsupported broker mode: {broker_mode}")

    @staticmethod
    def get_broker_config(broker_type: str) -> Dict[str, Any]:
        """获取券商配置"""
        config = {"account_id": get_config_value(f"{broker_type.upper()}_ACCOUNT_ID", "default")}

        if broker_type == "gjzj":
            config.update({
                "session_id": int(get_config_value("GJZJ_SESSION_ID", "0")),
                "strategy_name": get_config_value("GJZJ_STRATEGY_NAME", "AI-Trader"),
                "path": get_config_value("GJZJ_PATH"),
            })
        elif broker_type == "futu":
            config.update({
                "host": get_config_value("FUTU_HOST", "127.0.0.1"),
                "port": int(get_config_value("FUTU_PORT", "11111")),
                "market": get_config_value("FUTU_MARKET", "US"),
                "security_firm": get_config_value("FUTU_SECURITY_FIRM", ""),
            })
            
        return config
