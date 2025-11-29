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
        """从账户列表中选择账户ID，保持原始类型"""
        if acc_list is None or len(acc_list) == 0:
            return None

        if 'acc_id' in acc_list.columns:
            # 获取所有可用的账户ID
            available_acc_ids = acc_list['acc_id'].tolist()

            # 如果配置了账户ID且不是"default"，尝试匹配
            if self.account_id and self.account_id != "default":
                # 尝试字符串匹配
                matching = acc_list[acc_list['acc_id'].astype(str) == str(self.account_id)]
                if len(matching) > 0:
                    # 保持原始类型
                    return matching.iloc[0]['acc_id']

                # 如果字符串匹配失败，尝试数字匹配
                try:
                    account_id_num = int(self.account_id)
                    matching = acc_list[acc_list['acc_id'] == account_id_num]
                    if len(matching) > 0:
                        # 保持原始类型
                        return matching.iloc[0]['acc_id']
                except (ValueError, TypeError):
                    pass

                # 如果配置的账户ID不存在，打印警告并使用第一个可用账户ID
                print(f"⚠️ 警告: 配置的账户ID '{self.account_id}' 不存在")
                print(f"可用的账户ID: {available_acc_ids}")
                print(f"将使用第一个可用账户ID: {available_acc_ids[0]}")

            # 返回第一个账户ID（保持原始类型）
            return acc_list['acc_id'].iloc[0]

        # 如果没有acc_id列，尝试从第一行获取
        if len(acc_list) > 0:
            first_row = acc_list.iloc[0]
            if hasattr(first_row, 'acc_id'):
                return first_row['acc_id']
            elif 'acc_id' in first_row:
                return first_row['acc_id']

        return None

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
                # 根据市场类型选择测试股票代码
                test_symbol = "US.AAPL" if self.market.upper() == "US" else "HK.00700"
                ret, _ = self._quote_ctx.get_market_state([test_symbol])
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
                    # 如果 security_firm 为空，不传递该参数
                    if self.security_firm:
                        self._trade_ctx = ctx_class(host=self.host, port=self.port, security_firm=self.security_firm)
                    else:
                        self._trade_ctx = ctx_class(host=self.host, port=self.port)

                    # 测试交易连接
                    ret, data = self._trade_ctx.accinfo_query(trd_env=TrdEnv.REAL)
                    if ret != RET_OK:
                        error_msg = str(data) if data else "未知错误"
                        print(f"⚠️ 警告: Futu交易连接测试失败，返回码: {ret}")
                        print(f"错误信息: {error_msg}")

                        # 如果是账户权限问题，提供更详细的提示
                        if "No available real accounts" in error_msg or "market authority" in error_msg:
                            print("=" * 60)
                            print("💡 解决方案：")
                            print("  1. 请确保FutuOpenD已登录并启用交易权限")
                            print("  2. 检查账户是否有对应市场的交易权限（当前市场: {})".format(self.market))
                            if self.market.upper() == "US":
                                print("  3. 如果账户需要指定券商，请在 .env 文件中设置 FUTU_SECURITY_FIRM")
                                print("     例如: FUTU_SECURITY_FIRM=FUTUSECURITIES")
                            print("=" * 60)
                        else:
                            print("提示: 请确保FutuOpenD已登录并启用交易权限")

                        self._trade_ctx.close()
                        self._trade_ctx = None
                    else:
                        print(f"✅ Futu交易上下文创建成功（市场: {self.market}）")
                else:
                    print(f"⚠️ 警告: 不支持的市场类型: {self.market}，支持: US, HK")
                    self._trade_ctx = None
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ 警告: 创建Futu交易上下文失败: {error_msg}")

                # 如果是账户权限问题，提供更详细的提示
                if "No available real accounts" in error_msg or "market authority" in error_msg:
                    print("=" * 60)
                    print("💡 解决方案：")
                    print("  1. 请确保FutuOpenD已登录并启用交易权限")
                    print("  2. 检查账户是否有对应市场的交易权限（当前市场: {})".format(self.market))
                    if self.market.upper() == "US":
                        print("  3. 如果账户需要指定券商，请在 .env 文件中设置 FUTU_SECURITY_FIRM")
                        print("     例如: FUTU_SECURITY_FIRM=FUTUSECURITIES")
                    print("=" * 60)
                else:
                    print("提示: 请确保FutuOpenD服务正在运行并已登录")

                import traceback
                traceback.print_exc()
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
                    # 尝试提取价格，按优先级顺序尝试多个字段
                    # 富途API可能返回的字段：last_price, cur_price, close_price, price, now_price等
                    price_fields = [
                        'last_price',      # 最新价
                        'cur_price',       # 当前价
                        'now_price',       # 现价
                        'price',           # 价格
                        'close_price',     # 收盘价
                        'prev_close_price', # 昨收价
                        'open_price',      # 开盘价
                    ]

                    for price_field in price_fields:
                        if price_field in data.columns:
                            try:
                                price_value = data[price_field].iloc[0]
                                # 处理NaN或None值
                                import math
                                if price_value is not None:
                                    # 检查是否为NaN
                                    if isinstance(price_value, float) and math.isnan(price_value):
                                        continue
                                    price = float(price_value)
                                    if price > 0:
                                        return price
                            except (ValueError, TypeError, IndexError):
                                continue

                    # 如果所有字段都失败，打印调试信息
                    available_columns = list(data.columns) if hasattr(data, 'columns') else []
                    print(f"⚠️ 警告: 富途API返回数据中没有找到有效的价格字段")
                    print(f"   股票代码: {futu_symbol}")
                    print(f"   可用字段: {available_columns}")
                    if len(data) > 0:
                        print(f"   第一行数据: {data.iloc[0].to_dict() if hasattr(data.iloc[0], 'to_dict') else str(data.iloc[0])}")
                else:
                    error_msg = data if isinstance(data, str) else "未知错误"
                    print(f"⚠️ 警告: 富途API获取价格失败，返回码: {ret}, 错误: {error_msg}")
            except Exception as e:
                print(f"⚠️ 警告: 使用富途API获取价格失败: {e}")
                import traceback
                traceback.print_exc()

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
        """获取账户信息

        Returns:
            包含 cash, total_asset 的字典

        Raises:
            RuntimeError: 如果交易上下文未创建或获取账户信息失败
        """
        if not (self._trade_ctx and self._connected):
            raise RuntimeError("交易上下文未创建，无法获取账户信息")

        try:
            from futu import RET_OK, TrdEnv
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK:
                raise RuntimeError(f"获取账户列表失败，返回码: {ret}, 错误信息: {acc_list}")
            if acc_list is None or len(acc_list) == 0:
                raise RuntimeError("未找到交易账户")

            # 打印账户列表信息（用于调试）
            if 'acc_id' in acc_list.columns:
                available_acc_ids = acc_list['acc_id'].tolist()
                print(f"📋 可用账户列表: {available_acc_ids}")
            else:
                print(f"📋 账户列表: {acc_list}")
                available_acc_ids = []

            # 获取首选账户ID
            preferred_acc_id = self._get_account_id(acc_list)
            if not preferred_acc_id:
                raise RuntimeError(f"无法确定账户ID。可用的账户ID: {available_acc_ids}")

            # 尝试查询账户信息，如果失败则尝试其他账户ID
            acc_ids_to_try = [preferred_acc_id]
            if 'acc_id' in acc_list.columns:
                # 添加其他账户ID作为备选
                for acc_id in available_acc_ids:
                    if acc_id != preferred_acc_id:
                        acc_ids_to_try.append(acc_id)

            last_error = None
            for acc_id in acc_ids_to_try:
                ret, data = self._trade_ctx.accinfo_query(trd_env=TrdEnv.REAL, acc_id=acc_id)
                if ret == RET_OK:
                    # 查询成功
                    if data is None or len(data) == 0:
                        last_error = RuntimeError("账户信息为空")
                        continue

                    row = data.iloc[0]
                    cash = float(row.get('cash', 0.0))
                    total_asset = float(row.get('total_assets', row.get('total_asset', row.get('net_cash', cash))))
                    return {"cash": cash, "total_asset": total_asset}
                else:
                    # 查询失败，记录错误并尝试下一个
                    error_msg = str(data) if data else "未知错误"
                    last_error = RuntimeError(
                        f"查询账户信息失败，返回码: {ret}, 错误信息: {error_msg}"
                    )
                    print(f"⚠️ 账户ID {acc_id} 查询失败: {error_msg}")
                    if acc_id != acc_ids_to_try[-1]:
                        print(f"🔄 尝试下一个账户ID...")
                        continue

            # 所有账户ID都失败了
            raise RuntimeError(
                f"所有账户ID查询都失败。\n"
                f"尝试的账户ID: {acc_ids_to_try}\n"
                f"最后一个错误: {last_error}\n"
                f"提示: 请检查FutuOpenD是否已登录并启用交易权限，或检查账户ID是否正确"
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"获取Futu账户信息失败: {e}")

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
            from futu import RET_OK, TrdSide, OrderType as FutuOrderType, TrdEnv

            # 标准化股票代码
            futu_symbol = self._normalize_symbol(symbol)

            # 获取账户ID
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK or acc_list is None or len(acc_list) == 0:
                return {
                    "success": False,
                    "error": "无法获取账户列表",
                    "symbol": symbol,
                }

            acc_id = self._get_account_id(acc_list)
            if not acc_id:
                return {
                    "success": False,
                    "error": "无法确定账户ID",
                    "symbol": symbol,
                }

            # 确定订单类型
            futu_order_type = FutuOrderType.MARKET if order_type == OrderType.MARKET else FutuOrderType.NORMAL

            # 下单
            ret, data = self._trade_ctx.place_order(
                price=0.0 if order_type == OrderType.MARKET else price,
                qty=amount,
                code=futu_symbol,
                trd_side=TrdSide.BUY,
                order_type=futu_order_type,
                trd_env=TrdEnv.REAL,
                acc_id=acc_id
            )

            if ret != RET_OK:
                error_msg = str(data) if data else "未知错误"
                return {
                    "success": False,
                    "error": f"Futu买入失败: {error_msg}",
                    "symbol": symbol,
                }

            # 获取订单ID
            order_id = data.get('order_id', [None])[0] if data is not None and len(data) > 0 else None

            # 等待一小段时间，让订单执行
            import time
            time.sleep(0.5)

            # 查询实际总持仓
            total_positions = self._fetch_total_positions()
            total_qty = total_positions.get(symbol, 0)

            # 记录到AI持仓管理器
            self.ai_position_manager.record_buy(
                symbol=symbol,
                amount=amount,
                price=price,
                total_position=total_qty
            )

            return {
                "success": True,
                "order_id": str(order_id) if order_id else "unknown",
                "message": "买入订单已提交",
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "ai_position": self.ai_position_manager.get_ai_position(symbol),
                "total_position": total_qty,
                "note": "订单已提交，实际持仓可能稍后更新",
            }

        except ImportError as e:
            return {
                "success": False,
                "error": f"Futu模块未安装: {str(e)}",
                "symbol": symbol,
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

        # 交易前检查
        is_ok, error_result = self._pre_trade_check(symbol, amount, price, order_type, is_buy=False)
        if not is_ok:
            return error_result

        # 查询券商账户总持仓（用于后续计算）
        total_positions = self._fetch_total_positions()
        total_qty = total_positions.get(symbol, 0)
        ai_qty = self.ai_position_manager.get_ai_position(symbol)

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
            from futu import RET_OK, TrdSide, OrderType as FutuOrderType, TrdEnv

            # 标准化股票代码
            futu_symbol = self._normalize_symbol(symbol)

            # 获取账户ID
            ret, acc_list = self._trade_ctx.get_acc_list()
            if ret != RET_OK or acc_list is None or len(acc_list) == 0:
                return {
                    "success": False,
                    "error": "无法获取账户列表",
                    "symbol": symbol,
                }

            acc_id = self._get_account_id(acc_list)
            if not acc_id:
                return {
                    "success": False,
                    "error": "无法确定账户ID",
                    "symbol": symbol,
                }

            # 确定订单类型
            futu_order_type = FutuOrderType.MARKET if order_type == OrderType.MARKET else FutuOrderType.NORMAL

            # 下单
            ret, data = self._trade_ctx.place_order(
                price=0.0 if order_type == OrderType.MARKET else price,
                qty=amount,
                code=futu_symbol,
                trd_side=TrdSide.SELL,
                order_type=futu_order_type,
                trd_env=TrdEnv.REAL,
                acc_id=acc_id
            )

            if ret != RET_OK:
                error_msg = str(data) if data else "未知错误"
                return {
                    "success": False,
                    "error": f"Futu卖出失败: {error_msg}",
                    "symbol": symbol,
                }

            # 获取订单ID
            order_id = data.get('order_id', [None])[0] if data is not None and len(data) > 0 else None

            # 等待一小段时间，让订单执行
            import time
            time.sleep(0.5)

            # 查询实际总持仓
            new_total_positions = self._fetch_total_positions()
            new_total_qty = new_total_positions.get(symbol, 0)

            # 更新AI持仓管理器
            self.ai_position_manager.record_sell(
                symbol=symbol,
                amount=amount,
                price=price,
                total_position=new_total_qty
            )

            return {
                "success": True,
                "order_id": str(order_id) if order_id else "unknown",
                "message": f"卖出订单已提交，AI持仓剩余: {ai_qty - amount}",
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "ai_position": ai_qty - amount,
                "total_position": new_total_qty,
                "note": "订单已提交，实际持仓可能稍后更新",
            }

        except ImportError as e:
            return {
                "success": False,
                "error": f"Futu模块未安装: {str(e)}",
                "symbol": symbol,
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
