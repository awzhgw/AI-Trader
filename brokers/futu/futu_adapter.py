"""
Futu适配器（美股）
"""
from typing import Dict, Optional, Any

from brokers.base_broker import BaseBroker, OrderType
from tools.general_tools import get_config_value


class FutuAdapter(BaseBroker):
    """Futu适配器（美股）"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 配置字典，包含 account_id, host, port, market 等
        """
        super().__init__(config)
        self.host = config.get("host", "127.0.0.1")
        self.port = int(config.get("port", 11111))
        self.market = config.get("market", "US")
        self.security_firm = config.get("security_firm", "")
        self.real_trade = config.get("real_trade", False)
        self._quote_ctx = None

    @classmethod
    def create_from_config(cls) -> 'FutuAdapter':
        """从环境变量创建适配器"""
        from brokers.broker_factory import BrokerAdapterFactory
        config = BrokerAdapterFactory.get_broker_config("futu")
        return cls(config)

    def _get_broker_type(self) -> str:
        return "futu"

    def connect(self) -> bool:
        """
        连接到Futu API

        Returns:
            是否连接成功
        """
        try:
            # TODO: 实现实际的Futu连接逻辑
            # from futu import OpenQuoteContext, OpenHKTradeContext
            #
            # self._quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            # if self.real_trade:
            #     self._trade_ctx = OpenHKTradeContext(host=self.host, port=self.port,
            #                                           security_firm=self.security_firm)
            # return True
            return True
        except Exception as e:
            print(f"Futu连接失败: {e}")
            return False

    def get_price(self, symbol: str) -> float:
        """获取股票当前价格"""
        from tools.price_tools import get_open_prices
        today_date = get_config_value("TODAY_DATE")
        if not today_date:
            from datetime import datetime
            today_date = datetime.now().strftime("%Y-%m-%d")

        prices = get_open_prices(today_date, [symbol], market="us")
        price_key = f"{symbol}_price"
        price = prices.get(price_key)
        if price is None:
            raise ValueError(f"无法获取 {symbol} 的价格数据")
        return price

    def _fetch_total_positions(self) -> Dict[str, int]:
        """
        从券商API获取总持仓

        Returns:
            {symbol: quantity} 字典
        """
        try:
            # TODO: 实现实际的Futu持仓查询
            # if self._trade_ctx:
            #     ret, data = self._trade_ctx.position_list_query()
            #     if ret == 0:
            #         positions = {}
            #         for _, row in data.iterrows():
            #             symbol = row['code']
            #             qty = int(row['qty'])
            #             positions[symbol] = qty
            #         return positions
            return {}
        except Exception as e:
            print(f"获取Futu持仓失败: {e}")
            return {}

    def _fetch_account_info(self) -> Dict[str, float]:
        """
        获取账户信息

        Returns:
            包含 cash, total_asset 等的字典
        """
        try:
            # TODO: 实现实际的Futu账户查询
            # if self._trade_ctx:
            #     ret, data = self._trade_ctx.accinfo_query()
            #     if ret == 0:
            #         return {
            #             "cash": float(data['cash'][0]),
            #             "total_asset": float(data['total_assets'][0])
            #         }
            return {"cash": 0.0, "total_asset": 0.0}
        except Exception as e:
            print(f"获取Futu账户信息失败: {e}")
            return {"cash": 0.0, "total_asset": 0.0}

    def buy(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """买入股票"""

        # 获取价格
        if price is None:
            try:
                price = self.get_price(symbol)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "symbol": symbol,
                }

        # 调用Futu API买入
        try:
            # TODO: 实现实际的Futu买入逻辑
            # if self._trade_ctx:
            #     if order_type == OrderType.MARKET:
            #         ret, data = self._trade_ctx.place_order(price=0, qty=amount,
            #                                                code=symbol, trd_side=TrdSide.BUY,
            #                                                order_type=OrderType.MARKET)
            #     else:
            #         ret, data = self._trade_ctx.place_order(price=price, qty=amount,
            #                                                code=symbol, trd_side=TrdSide.BUY,
            #                                                order_type=OrderType.LIMIT)
            #     if ret != 0:
            #         raise Exception(f"Futu买入失败: {data}")

            # 模拟返回
            result = {
                "order_id": f"FUTU_{symbol}_{amount}_{price}",
                "status": "success"
            }

            # 查询总持仓
            total_positions = self._fetch_total_positions()
            total_qty = total_positions.get(symbol, 0) + amount  # 假设买入成功

            # 记录到AI持仓管理器
            self.ai_position_manager.record_buy(
                symbol=symbol,
                amount=amount,
                price=price,
                total_position=total_qty
            )

            return {
                "success": True,
                "order_id": result.get("order_id", ""),
                "message": "买入成功",
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "ai_position": self.ai_position_manager.get_ai_position(symbol),
                "total_position": total_qty,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Futu买入失败: {str(e)}",
                "symbol": symbol,
            }

    def sell(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """卖出股票（保护人工持仓）"""

        # 查询券商账户总持仓
        total_positions = self._fetch_total_positions()
        total_qty = total_positions.get(symbol, 0)

        # 查询AI持仓
        ai_qty = self.ai_position_manager.get_ai_position(symbol)

        # 检查是否可以卖出
        can_sell, reason = self._check_sell_permission(symbol, amount)
        if not can_sell:
            return {
                "success": False,
                "error": reason,
                "symbol": symbol,
                "amount": amount,
                "ai_position": ai_qty,
                "total_position": total_qty,
                "manual_position": total_qty - ai_qty,
            }

        # 获取价格
        if price is None:
            try:
                price = self.get_price(symbol)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "symbol": symbol,
                }

        # 调用Futu API卖出
        try:
            # TODO: 实现实际的Futu卖出逻辑
            # if self._trade_ctx:
            #     if order_type == OrderType.MARKET:
            #         ret, data = self._trade_ctx.place_order(price=0, qty=amount,
            #                                                code=symbol, trd_side=TrdSide.SELL,
            #                                                order_type=OrderType.MARKET)
            #     else:
            #         ret, data = self._trade_ctx.place_order(price=price, qty=amount,
            #                                                code=symbol, trd_side=TrdSide.SELL,
            #                                                order_type=OrderType.LIMIT)
            #     if ret != 0:
            #         raise Exception(f"Futu卖出失败: {data}")

            # 模拟返回
            result = {
                "order_id": f"FUTU_SELL_{symbol}_{amount}_{price}",
                "status": "success"
            }

            # 更新AI持仓管理器
            new_total_qty = max(0, total_qty - amount)
            self.ai_position_manager.record_sell(
                symbol=symbol,
                amount=amount,
                price=price,
                total_position=new_total_qty
            )

            return {
                "success": True,
                "order_id": result.get("order_id", ""),
                "message": f"卖出成功，AI持仓剩余: {ai_qty - amount}",
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "ai_position": ai_qty - amount,
                "total_position": new_total_qty,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Futu卖出失败: {str(e)}",
                "symbol": symbol,
            }

    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取持仓（区分总持仓和AI持仓）"""

        # 从券商API获取总持仓
        total_positions = self._fetch_total_positions()

        # 从AI持仓管理器获取AI持仓
        ai_positions = self.ai_position_manager.get_all_ai_positions()

        # 计算人工持仓
        manual_positions = {}
        for sym, total_qty in total_positions.items():
            ai_qty = ai_positions.get(sym, 0)
            manual_qty = total_qty - ai_qty
            if manual_qty > 0:
                manual_positions[sym] = manual_qty

        # 获取账户信息
        account_info = self._fetch_account_info()

        result = {
            "total_positions": total_positions,
            "ai_positions": ai_positions,
            "manual_positions": manual_positions,
            "cash": account_info.get("cash", 0.0),
            "total_asset": account_info.get("total_asset", 0.0),
        }

        # 如果指定了symbol，只返回该股票的信息
        if symbol:
            return {
                "symbol": symbol,
                "total_position": total_positions.get(symbol, 0),
                "ai_position": ai_positions.get(symbol, 0),
                "manual_position": manual_positions.get(symbol, 0),
            }

        return result
