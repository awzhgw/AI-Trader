"""
XtQuant适配器（A股）
基于迅投XtQuant交易模块
参考文档: https://dict.thinktrader.net/nativeApi/xttrader.html
"""
from typing import Dict, Optional, Any, List

from brokers.base_broker import BaseBroker, OrderType
from tools.general_tools import get_config_value


class XtQuantAdapter(BaseBroker):
    """XtQuant适配器（A股）"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 配置字典，包含 account_id, session_id 等
        """
        super().__init__(config)
        self.account_id = config.get("account_id", "default")
        self.session_id = config.get("session_id", 0)  # 会话ID
        self.trader = config.get("trader", None)  # XtQuantTrader实例
        self._connected = False

    @classmethod
    def create_from_config(cls) -> 'XtQuantAdapter':
        """从环境变量创建适配器"""
        from brokers.broker_factory import BrokerAdapterFactory
        config = BrokerAdapterFactory.get_broker_config("xtquant")
        return cls(config)

    def _get_broker_type(self) -> str:
        return "xtquant"

    def connect(self) -> bool:
        """
        连接到XtQuant交易系统

        Returns:
            是否连接成功
        """
        try:
            # 如果已经连接，直接返回
            if self._connected and self.trader is not None:
                return True

            # 尝试导入XtQuant模块
            try:
                from xtquant import xttrader
                from xtquant.xttype import StockAccount

                # 创建XtQuantTrader实例
                if self.trader is None:
                    # 创建API实例
                    self.trader = xttrader.XtQuantTrader()

                    # 注册回调类（可选）
                    # callback = MyXtQuantTraderCallback()
                    # self.trader.register_callback(callback)

                    # 准备API环境
                    self.trader.prepare()

                    # 创建连接
                    # 参数: session_id, account_type
                    # session_id: 会话ID，0表示使用默认会话
                    # account_type: 账号类型，StockAccount.STOCK_ACCOUNT表示股票账号
                    self.session_id = self.trader.start(session_id=self.session_id)

                    if self.session_id > 0:
                        self._connected = True
                        return True
                    else:
                        print(f"XtQuant连接失败: session_id={self.session_id}")
                        return False
                else:
                    self._connected = True
                    return True

            except ImportError as e:
                print(f"⚠️ 警告: 未安装XtQuant模块: {e}")
                print("请安装XtQuant: pip install xtquant")
                return False
            except Exception as e:
                print(f"XtQuant连接失败: {e}")
                return False

        except Exception as e:
            print(f"XtQuant连接异常: {e}")
            return False

    def get_price(self, symbol: str) -> float:
        """获取股票当前价格"""
        # 优先使用XtQuant获取实时价格
        if self.trader is not None and self._connected:
            try:
                # XtQuant可以通过行情模块获取价格
                # 这里先回退到本地数据，实际使用时可以通过XtData模块获取
                pass
            except Exception as e:
                print(f"XtQuant获取价格失败，回退到本地数据: {e}")

        # 回退到本地数据
        from tools.price_tools import get_open_prices
        today_date = get_config_value("TODAY_DATE")
        if not today_date:
            from datetime import datetime
            today_date = datetime.now().strftime("%Y-%m-%d")

        prices = get_open_prices(today_date, [symbol], market="cn")
        price_key = f"{symbol}_price"
        price = prices.get(price_key)
        if price is None:
            raise ValueError(f"无法获取 {symbol} 的价格数据")
        return price

    def _fetch_total_positions(self) -> Dict[str, int]:
        """
        从XtQuant获取总持仓

        Returns:
            {symbol: quantity} 字典
        """
        try:
            if self.trader is not None and self._connected:
                # XtQuant API: query_stock_positions
                # 参数: account_id, account_type
                from xtquant.xttype import StockAccount

                positions = self.trader.query_stock_positions(
                    account_id=self.account_id,
                    account_type=StockAccount.STOCK_ACCOUNT
                )

                if positions:
                    result = {}
                    for pos in positions:
                        # pos是XtPosition对象
                        # 字段: stock_code, can_use_volume, volume等
                        stock_code = pos.stock_code
                        volume = int(pos.volume) if hasattr(pos, 'volume') else 0
                        if volume > 0:
                            result[stock_code] = volume
                    return result
            else:
                print("⚠️ 警告: XtQuant未连接，无法获取真实持仓")
                return {}
        except Exception as e:
            print(f"获取XtQuant持仓失败: {e}")
            return {}

    def _fetch_account_info(self) -> Dict[str, float]:
        """
        获取账户信息

        Returns:
            包含 cash, total_asset 等的字典
        """
        try:
            if self.trader is not None and self._connected:
                # XtQuant API: query_stock_asset
                # 参数: account_id, account_type
                from xtquant.xttype import StockAccount

                asset = self.trader.query_stock_asset(
                    account_id=self.account_id,
                    account_type=StockAccount.STOCK_ACCOUNT
                )

                if asset:
                    # asset是XtAsset对象
                    # 字段: cash, total_asset等
                    return {
                        "cash": float(asset.cash) if hasattr(asset, 'cash') else 0.0,
                        "total_asset": float(asset.total_asset) if hasattr(asset, 'total_asset') else 0.0
                    }
            else:
                return {"cash": 0.0, "total_asset": 0.0}
        except Exception as e:
            print(f"获取XtQuant账户信息失败: {e}")
            return {"cash": 0.0, "total_asset": 0.0}

    def buy(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """买入股票"""

        # A股必须100的倍数
        if amount % 100 != 0:
            return {
                "success": False,
                "error": f"Chinese A-shares must be traded in multiples of 100 shares. You tried to buy {amount} shares.",
                "symbol": symbol,
                "amount": amount,
            }

        # 检查连接
        if not self._connected or self.trader is None:
            return {
                "success": False,
                "error": "XtQuant未连接，请先调用connect()方法",
                "symbol": symbol,
            }

        # 获取价格（限价单需要）
        if order_type == OrderType.LIMIT and price is None:
            try:
                price = self.get_price(symbol)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "symbol": symbol,
                }

        # 调用XtQuant API买入
        try:
            from xtquant.xttype import StockAccount

            # XtQuant API: order_stock
            # 参数: account_id, account_type, order_type, stock_code, order_volume, price_type, price, strategy_name, order_remark
            # order_type: 委托类型，1=买入，2=卖出
            # price_type: 报价类型，0=限价，4=市价

            order_type_code = 1  # 买入
            price_type = 0 if order_type == OrderType.LIMIT else 4  # 0=限价，4=市价
            order_price = price if order_type == OrderType.LIMIT else 0.0

            strategy_name = get_config_value("XTQUANT_STRATEGY_NAME", "AI-Trader")
            order_remark = f"XtQuant买入 {symbol} {amount}股"

            # 同步下单
            order_id = self.trader.order_stock(
                account_id=self.account_id,
                account_type=StockAccount.STOCK_ACCOUNT,
                order_type=order_type_code,
                stock_code=symbol,
                order_volume=amount,
                price_type=price_type,
                price=order_price,
                strategy_name=strategy_name,
                order_remark=order_remark
            )

            if order_id > 0:
                # 查询总持仓
                total_positions = self._fetch_total_positions()
                total_qty = total_positions.get(symbol, 0) + amount  # 假设买入成功

                # 记录到AI持仓管理器
                actual_price = price if price else self.get_price(symbol)
                self.ai_position_manager.record_buy(
                    symbol=symbol,
                    amount=amount,
                    price=actual_price,
                    total_position=total_qty
                )

                return {
                    "success": True,
                    "order_id": str(order_id),
                    "message": "买入成功",
                    "symbol": symbol,
                    "amount": amount,
                    "price": actual_price,
                    "ai_position": self.ai_position_manager.get_ai_position(symbol),
                    "total_position": total_qty,
                }
            else:
                return {
                    "success": False,
                    "error": f"XtQuant买入失败: order_id={order_id}",
                    "symbol": symbol,
                }

        except ImportError as e:
            return {
                "success": False,
                "error": f"XtQuant模块未安装: {str(e)}",
                "symbol": symbol,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"XtQuant买入失败: {str(e)}",
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

        # A股必须100的倍数
        if amount % 100 != 0:
            return {
                "success": False,
                "error": f"Chinese A-shares must be traded in multiples of 100 shares. You tried to sell {amount} shares.",
                "symbol": symbol,
                "amount": amount,
            }

        # 检查连接
        if not self._connected or self.trader is None:
            return {
                "success": False,
                "error": "XtQuant未连接，请先调用connect()方法",
                "symbol": symbol,
            }

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

        # 获取价格（限价单需要）
        if order_type == OrderType.LIMIT and price is None:
            try:
                price = self.get_price(symbol)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "symbol": symbol,
                }

        # 调用XtQuant API卖出
        try:
            from xtquant.xttype import StockAccount

            # XtQuant API: order_stock
            order_type_code = 2  # 卖出
            price_type = 0 if order_type == OrderType.LIMIT else 4  # 0=限价，4=市价
            order_price = price if order_type == OrderType.LIMIT else 0.0

            strategy_name = get_config_value("XTQUANT_STRATEGY_NAME", "AI-Trader")
            order_remark = f"XtQuant卖出 {symbol} {amount}股"

            # 同步下单
            order_id = self.trader.order_stock(
                account_id=self.account_id,
                account_type=StockAccount.STOCK_ACCOUNT,
                order_type=order_type_code,
                stock_code=symbol,
                order_volume=amount,
                price_type=price_type,
                price=order_price,
                strategy_name=strategy_name,
                order_remark=order_remark
            )

            if order_id > 0:
                # 更新AI持仓管理器
                new_total_qty = max(0, total_qty - amount)
                actual_price = price if price else self.get_price(symbol)
                self.ai_position_manager.record_sell(
                    symbol=symbol,
                    amount=amount,
                    price=actual_price,
                    total_position=new_total_qty
                )

                return {
                    "success": True,
                    "order_id": str(order_id),
                    "message": f"卖出成功，AI持仓剩余: {ai_qty - amount}",
                    "symbol": symbol,
                    "amount": amount,
                    "price": actual_price,
                    "ai_position": ai_qty - amount,
                    "total_position": new_total_qty,
                }
            else:
                return {
                    "success": False,
                    "error": f"XtQuant卖出失败: order_id={order_id}",
                    "symbol": symbol,
                }

        except ImportError as e:
            return {
                "success": False,
                "error": f"XtQuant模块未安装: {str(e)}",
                "symbol": symbol,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"XtQuant卖出失败: {str(e)}",
                "symbol": symbol,
            }

    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取持仓（区分总持仓和AI持仓）"""

        # 从XtQuant API获取总持仓
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
