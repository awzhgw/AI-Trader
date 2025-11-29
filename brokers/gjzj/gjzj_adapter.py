"""
XtQuant适配器（A股）
基于迅投XtQuant交易模块
参考文档: https://dict.thinktrader.net/nativeApi/xttrader.html
"""
import os
from typing import Dict, Optional, Any, List

from brokers.base_broker import BaseBroker, OrderType
from tools.general_tools import get_config_value


class GjzjAdapter(BaseBroker):
    """Gjzj适配器（A股）"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 配置字典，包含 account_id, session_id, strategy_name, path 等
        """
        super().__init__(config)
        # account_id已经在BaseBroker中设置，这里不需要再设置
        # 但如果config中有account_id，BaseBroker会使用它
        self.session_id = config.get("session_id", 0)  # 会话ID
        self.strategy_name = config.get("strategy_name", "AI-Trader")  # 策略名称
        self.path = config.get("path", None)  # MiniQMT客户端userdata_mini路径
        self.trader = config.get("trader", None)  # XtQuantTrader实例
        self._connected = False

    @classmethod
    def create_from_config(cls) -> 'GjzjAdapter':
        """从环境变量创建适配器"""
        from brokers.broker_factory import BrokerAdapterFactory
        config = BrokerAdapterFactory.get_broker_config("gjzj")
        return cls(config)

    def _get_broker_type(self) -> str:
        return "gjzj"

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
                # 检查运行环境
                import platform
                if platform.system() != 'Windows':
                    print("⚠️ 警告: XtQuant库主要支持Windows系统")
                    print(f"当前系统: {platform.system()}")
                    print("在Linux/WSL环境中，XtQuant可能无法正常工作")
                    print("建议在Windows环境中使用，或使用模拟交易模式")

                from xtquant import xttrader
                from xtquant.xttype import StockAccount

                # 创建XtQuantTrader实例
                if self.trader is None:
                    # 检查path配置
                    if self.path is None:
                        print("⚠️ 警告: 未配置XtQuant path参数")
                        return False

                    # 检查路径是否存在
                    if not os.path.exists(self.path):
                        print(f"⚠️ 警告: 指定的路径不存在: {self.path}")
                        return False

                    # 创建API实例
                    # XtQuantTrader(path, session_id, callback=None)
                    self.trader = xttrader.XtQuantTrader(self.path, self.session_id)

                    # 注册回调类（可选）
                    # callback = MyXtQuantTraderCallback()
                    # self.trader.register_callback(callback)

                    # 启动交易线程
                    self.trader.start()

                    # 创建连接
                    # connect()返回0表示连接成功
                    connect_result = self.trader.connect()

                    if connect_result == 0:
                        self._connected = True
                        return True
                    else:
                        print(f"XtQuant连接失败: connect_result={connect_result}")
                        return False
                else:
                    self._connected = True
                    return True

            except ImportError as e:
                error_msg = str(e)
                print(f"⚠️ 警告: 无法导入XtQuant模块: {e}")
                if 'xtpythonclient' in error_msg:
                    print("错误原因: xtpythonclient模块无法加载")
                    print("可能的原因:")
                    print("  1. XtQuant库主要支持Windows系统，Linux/WSL环境可能无法正常工作")
                    print("  2. 缺少必要的系统依赖或DLL文件")
                    print("  3. Python版本不匹配")
                    print("\n建议:")
                    print("  - 在Windows环境中使用XtQuant")
                    print("  - 参考文档: http://dict.thinktrader.net/nativeApi/start_now.html")
                else:
                    print("请安装XtQuant: pip install xtquant")
                return False
            except Exception as e:
                print(f"XtQuant连接失败: {e}")
                import traceback
                print("详细错误信息:")
                traceback.print_exc()
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
                # 参数: account (StockAccount对象)
                from xtquant.xttype import StockAccount

                account = StockAccount(self.account_id, 'STOCK')
                positions = self.trader.query_stock_positions(account)

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
                    # positions为None或空列表时返回空字典
                    return {}
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
                # 参数: account (StockAccount对象)
                from xtquant.xttype import StockAccount

                account = StockAccount(self.account_id, 'STOCK')
                asset = self.trader.query_stock_asset(account)

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

        # 交易前检查
        is_ok, error_result = self._pre_trade_check(symbol, amount, price, order_type, is_buy=True)
        if not is_ok:
            return error_result

        # A股必须100的倍数
        if amount % 100 != 0:
            return {
                "success": False,
                "error": f"Chinese A-shares must be traded in multiples of 100 shares. You tried to buy {amount} shares.",
                "symbol": symbol,
                "amount": amount,
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
            # 参数: account, stock_code, order_type, order_volume, price_type, price, strategy_name, order_remark
            # account: StockAccount对象（包含account_id和account_type）
            # order_type: 委托类型，23=买入，24=卖出
            # price_type: 报价类型，0=限价，4=市价

            # 创建StockAccount对象
            account = StockAccount(self.account_id, 'STOCK')

            order_type_code = 23  # 买入（23=买，24=卖）
            price_type = 0 if order_type == OrderType.LIMIT else 4  # 0=限价，4=市价
            order_price = price if order_type == OrderType.LIMIT else 0.0

            order_remark = f"XtQuant买入 {symbol} {amount}股"

            # 同步下单
            order_id = self.trader.order_stock(
                account=account,
                stock_code=symbol,
                order_type=order_type_code,
                order_volume=amount,
                price_type=price_type,
                price=order_price,
                strategy_name=self.strategy_name,
                order_remark=order_remark
            )

            if order_id > 0:
                # 等待一小段时间，让订单执行
                import time
                time.sleep(0.5)

                # 查询实际总持仓（而不是假设）
                total_positions = self._fetch_total_positions()
                total_qty = total_positions.get(symbol, 0)

                # 如果查询到的持仓没有增加，可能是订单还在处理中
                # 这里我们仍然记录，因为订单已经提交成功
                # 实际持仓会在后续查询中更新

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
                    "message": "买入订单已提交",
                    "symbol": symbol,
                    "amount": amount,
                    "price": actual_price,
                    "ai_position": self.ai_position_manager.get_ai_position(symbol),
                    "total_position": total_qty,
                    "note": "订单已提交，实际持仓可能稍后更新",
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

        # 交易前检查
        is_ok, error_result = self._pre_trade_check(symbol, amount, price, order_type, is_buy=False)
        if not is_ok:
            return error_result

        # A股必须100的倍数
        if amount % 100 != 0:
            return {
                "success": False,
                "error": f"Chinese A-shares must be traded in multiples of 100 shares. You tried to sell {amount} shares.",
                "symbol": symbol,
                "amount": amount,
            }

        # 查询券商账户总持仓（用于后续计算）
        total_positions = self._fetch_total_positions()
        total_qty = total_positions.get(symbol, 0)
        ai_qty = self.ai_position_manager.get_ai_position(symbol)

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
            # 参数: account, stock_code, order_type, order_volume, price_type, price, strategy_name, order_remark
            # account: StockAccount对象（包含account_id和account_type）
            # order_type: 委托类型，23=买入，24=卖出

            # 创建StockAccount对象
            account = StockAccount(self.account_id, 'STOCK')

            order_type_code = 24  # 卖出（23=买，24=卖）
            price_type = 0 if order_type == OrderType.LIMIT else 4  # 0=限价，4=市价
            order_price = price if order_type == OrderType.LIMIT else 0.0

            order_remark = f"XtQuant卖出 {symbol} {amount}股"

            # 同步下单
            order_id = self.trader.order_stock(
                account=account,
                stock_code=symbol,
                order_type=order_type_code,
                order_volume=amount,
                price_type=price_type,
                price=order_price,
                strategy_name=self.strategy_name,
                order_remark=order_remark
            )

            if order_id > 0:
                # 等待一小段时间，让订单执行
                import time
                time.sleep(0.5)

                # 查询实际总持仓（而不是假设）
                new_total_positions = self._fetch_total_positions()
                new_total_qty = new_total_positions.get(symbol, 0)

                # 更新AI持仓管理器
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
                    "message": f"卖出订单已提交，AI持仓剩余: {ai_qty - amount}",
                    "symbol": symbol,
                    "amount": amount,
                    "price": actual_price,
                    "ai_position": ai_qty - amount,
                    "total_position": new_total_qty,
                    "note": "订单已提交，实际持仓可能稍后更新",
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
