"""
Futu适配器（美股）
"""
# 过滤富途库的DeprecationWarning警告
# 这些警告来自富途库内部使用的已弃用protobuf API，在模块导入时就会产生
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="futu")
warnings.filterwarnings("ignore", message=".*deprecated.*", category=DeprecationWarning)

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
        self._quote_ctx = None
        self._trade_ctx = None
        self._connected = False

    @classmethod
    def create_from_config(cls) -> 'FutuAdapter':
        """从环境变量创建适配器"""
        from brokers.broker_factory import BrokerAdapterFactory
        config = BrokerAdapterFactory.get_broker_config("futu")
        return cls(config)

    def _get_broker_type(self) -> str:
        return "futu"

    def _normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码格式（添加市场后缀）"""
        if self.market.upper() == "US" and not symbol.endswith('.US'):
            return f"US.{symbol}"
        elif self.market.upper() == "HK" and not symbol.endswith('.HK'):
            return f"HK.{symbol}"
        return symbol

    def _get_account_id(self, acc_list) -> Optional[str]:
        """从账户列表中选择账户ID"""
        if acc_list is None or len(acc_list) == 0:
            return None

        if 'acc_id' in acc_list.columns:
            if self.account_id and self.account_id != "default":
                matching = acc_list[acc_list['acc_id'] == self.account_id]
                if len(matching) > 0:
                    return self.account_id
            return acc_list['acc_id'].iloc[0]
        return acc_list.iloc[0].get('acc_id') if hasattr(acc_list.iloc[0], 'acc_id') else None

    def connect(self) -> bool:
        """
        连接到Futu API

        Returns:
            是否连接成功
        """
        try:
            # 如果已经连接，直接返回
            if self._connected:
                return True

            # 尝试导入Futu模块
            try:
                # 在导入futu模块之前，先过滤DeprecationWarning警告
                import warnings
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                warnings.simplefilter("ignore", DeprecationWarning)

                from futu import (
                    OpenQuoteContext,
                    OpenUSTradeContext,
                    OpenHKTradeContext,
                    RET_OK,
                    TrdEnv
                )
            except ImportError as e:
                print(f"⚠️ 警告: 无法导入Futu模块: {e}")
                print("请安装Futu API: pip install futu-api")
                print("并确保FutuOpenD服务正在运行")
                return False

            # 创建行情上下文
            try:
                self._quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
                ret, _ = self._quote_ctx.get_market_state(['US.AAPL'])
                if ret != RET_OK:
                    self._quote_ctx.close()
                    self._quote_ctx = None
            except Exception as e:
                print(f"⚠️ 警告: 创建Futu行情上下文失败: {e}")
                self._quote_ctx = None

            # 创建交易上下文
            try:
                trade_ctx_map = {
                    "US": OpenUSTradeContext,
                    "HK": OpenHKTradeContext
                }
                ctx_class = trade_ctx_map.get(self.market.upper())
                if ctx_class:
                    self._trade_ctx = ctx_class(host=self.host, port=self.port, security_firm=self.security_firm)
                    ret, _ = self._trade_ctx.accinfo_query(trd_env=TrdEnv.REAL)
                    if ret != RET_OK:
                        self._trade_ctx.close()
                        self._trade_ctx = None
                else:
                    print(f"⚠️ 警告: 不支持的市场类型: {self.market}，支持: US, HK")
                    self._trade_ctx = None
            except Exception as e:
                print(f"⚠️ 警告: 创建Futu交易上下文失败: {e}")
                self._trade_ctx = None

            # 如果至少行情连接成功，认为连接成功
            if self._quote_ctx:
                self._connected = True
                return True
            else:
                print("❌ Futu连接失败: 无法建立行情连接")
                return False

        except Exception as e:
            print(f"Futu连接失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_price(self, symbol: str) -> float:
        """获取股票当前价格"""
        # 优先使用富途API获取实时价格
        if self._quote_ctx and self._connected:
            try:
                from futu import RET_OK
                futu_symbol = self._normalize_symbol(symbol)
                ret, data = self._quote_ctx.get_market_snapshot([futu_symbol])

                if ret == RET_OK and data is not None and len(data) > 0:
                    # 尝试提取价格
                    for price_field in ['last_price', 'cur_price', 'close_price']:
                        if price_field in data.columns:
                            price = float(data[price_field].iloc[0])
                            if price > 0:
                                return price
                    print(f"⚠️ 警告: 富途API返回数据中没有找到价格字段，可用字段: {list(data.columns)}")
            except Exception as e:
                print(f"⚠️ 警告: 使用富途API获取价格失败: {e}")

        # 回退到本地数据
        from tools.price_tools import get_open_prices
        today_date = get_config_value("TODAY_DATE") or __import__('datetime').datetime.now().strftime("%Y-%m-%d")
        prices = get_open_prices(today_date, [symbol], market="us")
        price = prices.get(f"{symbol}_price")
        if price is None:
            raise ValueError(f"无法获取 {symbol} 的价格数据（富途API和本地数据都不可用）")
        return price

    def _fetch_total_positions(self) -> Dict[str, int]:
        """从券商API获取总持仓"""
        if not (self._trade_ctx and self._connected):
            return {}

        try:
            from futu import RET_OK, TrdEnv
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK or acc_list is None or len(acc_list) == 0:
                return {}

            acc_id = self._get_account_id(acc_list)
            if not acc_id:
                return {}

            ret, data = self._trade_ctx.position_list_query(trd_env=TrdEnv.REAL, acc_id=acc_id)
            if ret != RET_OK or data is None:
                return {}

            positions = {}
            for _, row in data.iterrows():
                symbol = row.get('code', '')
                qty = int(row.get('qty', 0) or row.get('can_sell_qty', 0))
                if qty > 0 and symbol:
                    # 美股去掉市场后缀
                    if self.market.upper() == "US" and symbol.endswith('.US'):
                        symbol = symbol[:-3]
                    positions[symbol] = qty
            return positions
        except Exception as e:
            print(f"获取Futu持仓失败: {e}")
            return {}

    def _fetch_account_info(self) -> Dict[str, float]:
        """获取账户信息"""
        if not (self._trade_ctx and self._connected):
            return {"cash": 0.0, "total_asset": 0.0}

        try:
            from futu import RET_OK, TrdEnv
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK or acc_list is None or len(acc_list) == 0:
                return {"cash": 0.0, "total_asset": 0.0}

            acc_id = self._get_account_id(acc_list)
            if not acc_id:
                return {"cash": 0.0, "total_asset": 0.0}

            ret, data = self._trade_ctx.accinfo_query(trd_env=TrdEnv.REAL, acc_id=acc_id)
            if ret != RET_OK or data is None or len(data) == 0:
                return {"cash": 0.0, "total_asset": 0.0}

            row = data.iloc[0]
            cash = float(row.get('cash', 0.0))
            total_asset = float(row.get('total_assets', row.get('total_asset', row.get('net_cash', cash))))
            return {"cash": cash, "total_asset": total_asset}
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
