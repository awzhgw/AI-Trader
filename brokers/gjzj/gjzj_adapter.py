"""
XtQuant适配器（A股）
基于迅投XtQuant交易模块
参考文档: https://dict.thinktrader.net/nativeApi/xttrader.html
"""
import os
from typing import Dict, Optional, Any

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
        """连接到XtQuant交易系统"""
        if self._connected and self.trader:
            return True

        try:
            import platform
            if platform.system() != 'Windows':
                print(f"⚠️ 警告: XtQuant主要支持Windows，当前系统: {platform.system()}")

            from xtquant import xttrader
            
            if not self.path or not os.path.exists(self.path):
                print(f"⚠️ 警告: 无效的XtQuant路径: {self.path}")
                return False

            if self.trader is None:
                self.trader = xttrader.XtQuantTrader(self.path, self.session_id)
                self.trader.start()
                if self.trader.connect() != 0:
                    print("XtQuant连接失败")
                    return False
            
            self._connected = True
            return True

        except ImportError:
            print("⚠️ 无法导入XtQuant，请检查环境和依赖")
            return False
        except Exception as e:
            print(f"XtQuant连接异常: {e}")
            return False

    def get_price(self, symbol: str) -> float:
        """获取股票当前价格"""
        try:
            from xtquant import xtdata
            tick = xtdata.get_full_tick([symbol])
            price = tick.get(symbol, {}).get('lastPrice')
            if price and price > 0:
                return float(price)
        except Exception as e:
            print(f"XtQuant获取价格失败: {e}")

        raise ValueError(f"无法获取 {symbol} 的价格数据")

    def _fetch_total_positions(self) -> Dict[str, int]:
        """获取真实持仓"""
        if not (self.trader and self._connected):
            return {}
            
        try:
            from xtquant.xttype import StockAccount
            account = StockAccount(self.account_id, 'STOCK')
            positions = self.trader.query_stock_positions(account)
            
            return {
                pos.stock_code: int(pos.volume)
                for pos in positions
                if pos.volume > 0
            } if positions else {}
        except Exception as e:
            print(f"获取持仓失败: {e}")
            return {}

    def _fetch_account_info(self) -> Dict[str, float]:
        """获取账户资金"""
        default = {"cash": 0.0, "total_asset": 0.0}
        if not (self.trader and self._connected):
            return default
            
        try:
            from xtquant.xttype import StockAccount
            account = StockAccount(self.account_id, 'STOCK')
            asset = self.trader.query_stock_asset(account)
            
            if asset:
                return {
                    "cash": float(asset.cash),
                    "total_asset": float(asset.total_asset)
                }
            return default
        except Exception as e:
            print(f"获取账户信息失败: {e}")
            return default

    def _trade(self, symbol: str, amount: int, price: Optional[float], order_type: OrderType, is_buy: bool) -> Dict[str, Any]:
        """统一交易逻辑"""
        # 1. 基础检查
        is_ok, error = self._pre_trade_check(symbol, amount, price, order_type, is_buy)
        if not is_ok: return error
        
        # 2. A股手数检查
        if amount % 100 != 0:
            return {
                "success": False,
                "error": f"A股交易数量必须是100的倍数，当前: {amount}",
                "symbol": symbol
            }

        # 3. 价格检查
        if order_type == OrderType.LIMIT and price is None:
            try:
                price = self.get_price(symbol)
            except ValueError as e:
                return {"success": False, "error": str(e), "symbol": symbol}
        
        # 4. 执行交易
        try:
            from xtquant.xttype import StockAccount
            account = StockAccount(self.account_id, 'STOCK')
            
            xt_order_type = 23 if is_buy else 24
            price_type = 0 if order_type == OrderType.LIMIT else 4
            exec_price = price if order_type == OrderType.LIMIT else 0.0
            action_str = "买入" if is_buy else "卖出"
            
            order_id = self.trader.order_stock(
                account=account,
                stock_code=symbol,
                order_type=xt_order_type,
                order_volume=amount,
                price_type=price_type,
                price=exec_price,
                strategy_name=self.strategy_name,
                order_remark=f"XtQuant{action_str} {symbol} {amount}股"
            )
            
            if order_id <= 0:
                return {"success": False, "error": f"下单失败: {order_id}", "symbol": symbol}
                
            # 5. 后处理
            import time
            time.sleep(0.5)
            
            total_pos = self._fetch_total_positions().get(symbol, 0)
            actual_price = price or self.get_price(symbol)
            
            if is_buy:
                self.ai_position_manager.record_buy(symbol, amount, actual_price, total_pos)
            else:
                self.ai_position_manager.record_sell(symbol, amount, actual_price, total_pos)
                
            ai_pos = self.ai_position_manager.get_ai_position(symbol)
            
            return {
                "success": True,
                "order_id": str(order_id),
                "message": f"{action_str}订单已提交",
                "symbol": symbol,
                "amount": amount,
                "price": actual_price,
                "ai_position": ai_pos,
                "total_position": total_pos
            }
            
        except ImportError:
            return {"success": False, "error": "XtQuant模块未安装", "symbol": symbol}
        except Exception as e:
            return {"success": False, "error": f"交易异常: {str(e)}", "symbol": symbol}

    def buy(self, symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        return self._trade(symbol, amount, price, order_type, is_buy=True)

    def sell(self, symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        return self._trade(symbol, amount, price, order_type, is_buy=False)

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
