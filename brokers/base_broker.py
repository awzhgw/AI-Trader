"""
券商适配器抽象基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"  # 市价单
    LIMIT = "limit"    # 限价单


class BaseBroker(ABC):
    """券商适配器抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 配置字典，包含 account_id 等
        """
        self.config = config
        self.account_id = config.get("account_id", "default")
        self.broker_type = self._get_broker_type()

        # 初始化AI持仓管理器
        from brokers.ai_position_manager import AIPositionManager
        self.ai_position_manager = AIPositionManager(
            broker_type=self.broker_type,
            account_id=self.account_id
        )

    @abstractmethod
    def _get_broker_type(self) -> str:
        """返回券商类型: 'xtquant' | 'futu' | 'mock'"""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        连接到券商API

        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    def buy(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """
        买入股票

        流程：
        1. 调用券商API买入
        2. 查询总持仓
        3. 记录到AI持仓管理器

        Args:
            symbol: 股票代码
            amount: 买入数量
            price: 限价单价格（限价单时必需）
            order_type: 订单类型

        Returns:
            交易结果字典
        """
        pass

    @abstractmethod
    def sell(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """
        卖出股票（保护人工持仓）

        流程：
        1. 查询总持仓
        2. 查询AI持仓
        3. 检查是否可以卖出（AI持仓是否足够）
        4. 如果可以，调用券商API卖出
        5. 更新AI持仓管理器

        Args:
            symbol: 股票代码
            amount: 卖出数量
            price: 限价单价格（限价单时必需）
            order_type: 订单类型

        Returns:
            交易结果字典
        """
        pass

    @abstractmethod
    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        获取持仓信息

        Returns:
            {
                "total_positions": {symbol: quantity},  # 总持仓（包含人工）
                "ai_positions": {symbol: quantity},     # AI持仓
                "manual_positions": {symbol: quantity},  # 人工持仓（计算得出）
                "cash": float,
                "total_asset": float
            }
        """
        pass

    def _check_sell_permission(self, symbol: str, amount: int) -> Tuple[bool, str]:
        """
        检查是否可以卖出（保护人工持仓）

        Args:
            symbol: 股票代码
            amount: 卖出数量

        Returns:
            (是否可以卖出, 原因说明)
        """
        return self.ai_position_manager.can_sell(symbol, amount)

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """
        获取股票当前价格

        Args:
            symbol: 股票代码

        Returns:
            当前价格
        """
        pass
