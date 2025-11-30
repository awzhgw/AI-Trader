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

    def _get_account_id(self, acc_list) -> Optional[Any]:
        """从账户列表中选择账户ID"""
        if acc_list is None or acc_list.empty: return None

        # 1. 尝试使用配置的ID
        if self.account_id and self.account_id != "default" and 'acc_id' in acc_list.columns:
            # 尝试字符串匹配
            match = acc_list[acc_list['acc_id'].astype(str) == str(self.account_id)]
            if not match.empty: return match.iloc[0]['acc_id']
            
            # 尝试数字匹配
            try:
                match = acc_list[acc_list['acc_id'] == int(self.account_id)]
                if not match.empty: return match.iloc[0]['acc_id']
            except (ValueError, TypeError): pass
            
            print(f"⚠️ 配置ID {self.account_id} 不存在，使用默认")

        # 2. 返回第一个可用ID
        if 'acc_id' in acc_list.columns:
            return acc_list['acc_id'].iloc[0]
            
        # 3. 尝试直接获取
        return acc_list.iloc[0].get('acc_id')

    def connect(self) -> bool:
        """连接到Futu API"""
        if self._connected: return True

        try:
            import warnings
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from futu import OpenQuoteContext, OpenUSTradeContext, OpenHKTradeContext, RET_OK, TrdEnv

            # 1. 创建行情连接
            self._quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            test_sym = "US.AAPL" if self.market.upper() == "US" else "HK.00700"
            if self._quote_ctx.get_market_state([test_sym])[0] != RET_OK:
                self._quote_ctx.close()
                self._quote_ctx = None
                print("❌ Futu行情连接失败")
                return False

            # 2. 创建交易连接
            ctx_cls = OpenUSTradeContext if self.market.upper() == "US" else OpenHKTradeContext
            kwargs = {'host': self.host, 'port': self.port}
            if self.security_firm: kwargs['security_firm'] = self.security_firm
            
            self._trade_ctx = ctx_cls(**kwargs)
            ret, data = self._trade_ctx.accinfo_query(trd_env=TrdEnv.REAL)
            
            if ret != RET_OK:
                print(f"⚠️ Futu交易连接失败: {data}")
                self._trade_ctx.close()
                self._trade_ctx = None
                # 仅行情连接成功也算连接成功，但不能交易
            else:
                print(f"✅ Futu连接成功 ({self.market})")

            self._connected = True
            return True

        except ImportError:
            print("⚠️ 无法导入Futu模块，请安装 futu-api")
            return False
        except Exception as e:
            print(f"Futu连接异常: {e}")
            return False

    def get_price(self, symbol: str) -> float:
        """获取股票当前价格"""
        if self._quote_ctx and self._connected:
            try:
                from futu import RET_OK
                futu_symbol = self._normalize_symbol(symbol)
                ret, data = self._quote_ctx.get_market_snapshot([futu_symbol])
                
                if ret == RET_OK and not data.empty:
                    # 优先顺序: last_price > cur_price > close_price
                    for field in ['last_price', 'cur_price', 'close_price']:
                        if field in data.columns:
                            val = data[field].iloc[0]
                            if val and val > 0: return float(val)
            except Exception as e:
                print(f"Futu获取价格失败: {e}")

        # 回退到本地数据
        from tools.price_tools import get_open_prices
        from datetime import datetime
        today = get_config_value("TODAY_DATE") or datetime.now().strftime("%Y-%m-%d")
        price = get_open_prices(today, [symbol], market="us").get(f"{symbol}_price")
        
        if price is None:
            raise ValueError(f"无法获取 {symbol} 价格")
        return price

    def _fetch_total_positions(self) -> Dict[str, int]:
        """获取真实持仓"""
        if not (self._trade_ctx and self._connected): return {}
        
        try:
            from futu import RET_OK, TrdEnv
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK or acc_list.empty: return {}
            
            acc_id = self._get_account_id(acc_list)
            ret, data = self._trade_ctx.position_list_query(trd_env=TrdEnv.REAL, acc_id=acc_id)
            
            if ret != RET_OK or data.empty: return {}
            
            positions = {}
            for _, row in data.iterrows():
                sym = row.get('code', '')
                qty = int(row.get('qty', 0) or row.get('can_sell_qty', 0))
                if qty > 0 and sym:
                    if self.market.upper() == "US" and sym.endswith('.US'):
                        sym = sym[:-3]
                    positions[sym] = qty
            return positions
        except Exception as e:
            print(f"获取持仓失败: {e}")
            return {}

    def _fetch_account_info(self) -> Dict[str, float]:
        """获取账户资金"""
        if not (self._trade_ctx and self._connected):
            raise RuntimeError("未连接Futu")
            
        try:
            from futu import RET_OK, TrdEnv
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK or acc_list.empty:
                raise RuntimeError("无法获取账户列表")
                
            acc_id = self._get_account_id(acc_list)
            ret, data = self._trade_ctx.accinfo_query(trd_env=TrdEnv.REAL, acc_id=acc_id)
            
            if ret == RET_OK and not data.empty:
                row = data.iloc[0]
                cash = float(row.get('cash', 0.0))
                # 优先使用 total_assets, 其次 total_asset, 最后 net_cash
                total = float(row.get('total_assets', row.get('total_asset', row.get('net_cash', cash))))
                return {"cash": cash, "total_asset": total}
                
            raise RuntimeError(f"查询账户失败: {data}")
        except Exception as e:
            raise RuntimeError(f"获取账户信息异常: {e}")

    def _trade(self, symbol: str, amount: int, price: Optional[float], order_type: OrderType, is_buy: bool) -> Dict[str, Any]:
        """统一交易逻辑"""
        # 1. 基础检查
        is_ok, error = self._pre_trade_check(symbol, amount, price, order_type, is_buy)
        if not is_ok: return error

        # 2. 价格检查
        if price is None:
            try:
                price = self.get_price(symbol)
            except ValueError as e:
                return {"success": False, "error": str(e), "symbol": symbol}

        # 3. 执行交易
        try:
            from futu import RET_OK, TrdSide, OrderType as FutuOrderType, TrdEnv
            
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK or acc_list.empty:
                return {"success": False, "error": "无法获取账户列表", "symbol": symbol}
                
            acc_id = self._get_account_id(acc_list)
            if not acc_id:
                return {"success": False, "error": "无法确定账户ID", "symbol": symbol}

            futu_side = TrdSide.BUY if is_buy else TrdSide.SELL
            futu_type = FutuOrderType.MARKET if order_type == OrderType.MARKET else FutuOrderType.NORMAL
            exec_price = 0.0 if order_type == OrderType.MARKET else price
            
            ret, data = self._trade_ctx.place_order(
                price=exec_price,
                qty=amount,
                code=self._normalize_symbol(symbol),
                trd_side=futu_side,
                order_type=futu_type,
                trd_env=TrdEnv.REAL,
                acc_id=acc_id
            )

            if ret != RET_OK:
                return {"success": False, "error": f"下单失败: {data}", "symbol": symbol}

            # 4. 后处理
            order_id = str(data['order_id'][0]) if not data.empty else "unknown"
            import time
            time.sleep(0.5)
            
            total_pos = self._fetch_total_positions().get(symbol, 0)
            
            if is_buy:
                self.ai_position_manager.record_buy(symbol, amount, price, total_pos)
            else:
                self.ai_position_manager.record_sell(symbol, amount, price, total_pos)
            
            ai_pos = self.ai_position_manager.get_ai_position(symbol)
            action = "买入" if is_buy else "卖出"
            
            return {
                "success": True,
                "order_id": order_id,
                "message": f"{action}订单已提交",
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "ai_position": ai_pos,
                "total_position": total_pos
            }

        except ImportError:
            return {"success": False, "error": "Futu模块未安装", "symbol": symbol}
        except Exception as e:
            return {"success": False, "error": f"交易异常: {str(e)}", "symbol": symbol}

    def buy(self, symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        return self._trade(symbol, amount, price, order_type, is_buy=True)

    def sell(self, symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        return self._trade(symbol, amount, price, order_type, is_buy=False)

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
        try:
            account_info = self._fetch_account_info()
            cash = account_info.get("cash", 0.0)
            total_asset = account_info.get("total_asset", 0.0)
        except RuntimeError as e:
            # 如果获取账户信息失败，使用默认值并记录错误
            print(f"⚠️ 警告: {e}")
            cash = 0.0
            total_asset = 0.0

        result = {
            "total_positions": total_positions,
            "ai_positions": ai_positions,
            "manual_positions": manual_positions,
            "cash": cash,
            "total_asset": total_asset,
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
