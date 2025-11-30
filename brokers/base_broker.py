"""
券商适配器抽象基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Tuple
from enum import Enum
import logging

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"

class BaseBroker(ABC):
    """券商适配器抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_id = config.get("account_id", "default")
        self.broker_type = self._get_broker_type()
        
        self.logger = logging.getLogger(f"Broker.{self.broker_type}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        from brokers.ai_position_manager import AIPositionManager
        self.ai_position_manager = AIPositionManager(self.broker_type, self.account_id)

    @abstractmethod
    def _get_broker_type(self) -> str: pass

    @abstractmethod
    def connect(self) -> bool: pass

    @abstractmethod
    def buy(self, symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]: pass

    @abstractmethod
    def sell(self, symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]: pass

    @abstractmethod
    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]: pass

    @abstractmethod
    def get_price(self, symbol: str) -> float: pass

    def _check_sell_permission(self, symbol: str, amount: int) -> Tuple[bool, str]:
        return self.ai_position_manager.can_sell(symbol, amount)

    def _validate_order_params(self, symbol: str, amount: int, price: Optional[float], order_type: OrderType) -> Tuple[bool, Optional[str]]:
        if not symbol: return False, "股票代码不能为空"
        if amount <= 0: return False, f"数量必须>0: {amount}"
        if order_type == OrderType.LIMIT and (price is None or price <= 0): return False, "限价单需有效价格"
        return True, None

    def _pre_trade_check(self, symbol: str, amount: int, price: Optional[float], order_type: OrderType, is_buy: bool) -> Tuple[bool, Dict[str, Any]]:
        # 1. 参数验证
        ok, msg = self._validate_order_params(symbol, amount, price, order_type)
        if not ok: return False, {"success": False, "error": msg, "symbol": symbol}

        # 2. 连接检查
        if not self.connect():
             return False, {"success": False, "error": f"{self.broker_type}未连接", "symbol": symbol}

        # 3. 卖出权限检查
        if not is_buy:
            ok, reason = self._check_sell_permission(symbol, amount)
            if not ok:
                try:
                    pos = self.get_position(symbol)
                    ai, total = pos.get("ai_position", 0), pos.get("total_position", 0)
                except: ai = total = 0
                
                return False, {
                    "success": False, "error": reason, "symbol": symbol,
                    "ai_position": ai, "total_position": total
                }

        return True, {}
