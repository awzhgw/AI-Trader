"""
模拟交易适配器
兼容现有的模拟交易功能，同时支持AI持仓管理
"""
import os
import json
import fcntl
from typing import Dict, Optional, Any
from pathlib import Path

from brokers.base_broker import BaseBroker, OrderType
from tools.general_tools import get_config_value
from tools.price_tools import get_open_prices, get_latest_position, get_market_type


class MockAdapter(BaseBroker):
    """模拟交易适配器"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.signature = get_config_value("SIGNATURE", "default")
        self.today_date = get_config_value("TODAY_DATE")
        if not self.today_date:
            from datetime import datetime
            self.today_date = datetime.now().strftime("%Y-%m-%d")

        # 持仓文件路径
        self._position_file_path = self._get_position_file_path()
        self._ensure_position_dir()

    @classmethod
    def create_from_config(cls) -> 'MockAdapter':
        """从环境变量创建适配器"""
        config = {
            "account_id": get_config_value("SIGNATURE", "default")
        }
        return cls(config)

    def _get_broker_type(self) -> str:
        return "mock"

    def _get_position_file_path(self) -> Path:
        """获取持仓文件路径"""
        project_root = Path(__file__).resolve().parent.parent.parent
        log_path = get_config_value("LOG_PATH", "./data/agent_data")
        if log_path.startswith("./data/"):
            log_path = log_path[7:]

        return project_root / "data" / log_path / self.signature / "position" / "position.jsonl"

    def _ensure_position_dir(self):
        """确保持仓目录存在"""
        self._position_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _position_lock(self):
        """持仓文件锁"""
        class _Lock:
            def __init__(self, lock_path: Path):
                self.lock_path = lock_path.parent / ".position.lock"
                self._fh = open(self.lock_path, "a+")

            def __enter__(self):
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
                return self

            def __exit__(self, exc_type, exc, tb):
                try:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                finally:
                    self._fh.close()

        return _Lock(self._position_file_path)

    def connect(self) -> bool:
        """连接（模拟交易不需要连接）"""
        return True

    def get_price(self, symbol: str) -> float:
        """获取股票当前价格"""
        market = "cn" if symbol.endswith((".SH", ".SZ")) else "us"
        prices = get_open_prices(self.today_date, [symbol], market=market)
        price_key = f"{symbol}_price"
        price = prices.get(price_key)
        if price is None:
            raise ValueError(f"无法获取 {symbol} 的价格数据")
        return price

    def _get_current_position(self) -> tuple[Dict[str, float], int]:
        """获取当前持仓"""
        try:
            return get_latest_position(self.today_date, self.signature)
        except Exception as e:
            return {}, -1

    def _write_position_record(self, action: str, symbol: str, amount: int, new_position: Dict[str, float], action_id: int):
        """写入持仓记录"""
        record = {
            "date": self.today_date,
            "id": action_id + 1,
            "this_action": {
                "action": action,
                "symbol": symbol,
                "amount": amount
            },
            "positions": new_position
        }

        with open(self._position_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def buy(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """买入股票"""
        market = "cn" if symbol.endswith((".SH", ".SZ")) else "us"

        # A股必须100的倍数
        if market == "cn" and amount % 100 != 0:
            return {
                "success": False,
                "error": f"Chinese A-shares must be traded in multiples of 100 shares. You tried to buy {amount} shares.",
                "symbol": symbol,
                "amount": amount,
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

        # 获取当前持仓
        with self._position_lock():
            current_position, current_action_id = self._get_current_position()

            # 检查现金是否足够
            cash = current_position.get("CASH", 0.0)
            required_cash = price * amount

            if cash < required_cash:
                return {
                    "success": False,
                    "error": "Insufficient cash!",
                    "required_cash": required_cash,
                    "cash_available": cash,
                    "symbol": symbol,
                }

            # 更新持仓
            new_position = current_position.copy()
            new_position["CASH"] = cash - required_cash
            new_position[symbol] = new_position.get(symbol, 0) + amount

            # 写入记录
            self._write_position_record("buy", symbol, amount, new_position, current_action_id)

            # 获取总持仓（用于AI持仓管理器）
            total_position = new_position.get(symbol, 0)

            # 记录到AI持仓管理器
            self.ai_position_manager.record_buy(
                symbol=symbol,
                amount=amount,
                price=price,
                total_position=total_position
            )

            return {
                "success": True,
                "message": "买入成功",
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "ai_position": self.ai_position_manager.get_ai_position(symbol),
                "total_position": total_position,
                "cash": new_position["CASH"],
            }

    def sell(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """卖出股票（保护人工持仓）"""
        market = "cn" if symbol.endswith((".SH", ".SZ")) else "us"

        # A股必须100的倍数
        if market == "cn" and amount % 100 != 0:
            return {
                "success": False,
                "error": f"Chinese A-shares must be traded in multiples of 100 shares. You tried to sell {amount} shares.",
                "symbol": symbol,
                "amount": amount,
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

        # 获取当前持仓
        with self._position_lock():
            current_position, current_action_id = self._get_current_position()

            # 检查总持仓
            total_qty = current_position.get(symbol, 0)
            if total_qty < amount:
                return {
                    "success": False,
                    "error": "Insufficient shares!",
                    "have": total_qty,
                    "want_to_sell": amount,
                    "symbol": symbol,
                }

            # 检查AI持仓（保护人工持仓）
            can_sell, reason = self._check_sell_permission(symbol, amount)
            if not can_sell:
                ai_qty = self.ai_position_manager.get_ai_position(symbol)
                return {
                    "success": False,
                    "error": reason,
                    "symbol": symbol,
                    "amount": amount,
                    "ai_position": ai_qty,
                    "total_position": total_qty,
                    "manual_position": total_qty - ai_qty,
                }

            # 更新持仓
            new_position = current_position.copy()
            new_position[symbol] = total_qty - amount
            new_position["CASH"] = new_position.get("CASH", 0.0) + price * amount

            # 写入记录
            self._write_position_record("sell", symbol, amount, new_position, current_action_id)

            # 获取新的总持仓
            new_total_qty = new_position.get(symbol, 0)

            # 更新AI持仓管理器
            self.ai_position_manager.record_sell(
                symbol=symbol,
                amount=amount,
                price=price,
                total_position=new_total_qty
            )

            return {
                "success": True,
                "message": f"卖出成功，AI持仓剩余: {self.ai_position_manager.get_ai_position(symbol)}",
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "ai_position": self.ai_position_manager.get_ai_position(symbol),
                "total_position": new_total_qty,
                "cash": new_position["CASH"],
            }

    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取持仓信息"""
        current_position, _ = self._get_current_position()

        # 移除CASH字段，单独处理
        cash = current_position.pop("CASH", 0.0)
        total_positions = current_position.copy()

        # 获取AI持仓
        ai_positions = self.ai_position_manager.get_all_ai_positions()

        # 计算人工持仓
        manual_positions = {}
        for sym, total_qty in total_positions.items():
            ai_qty = ai_positions.get(sym, 0)
            manual_qty = total_qty - ai_qty
            if manual_qty > 0:
                manual_positions[sym] = manual_qty

        # 计算总资产
        total_asset = cash
        for sym, qty in total_positions.items():
            try:
                price = self.get_price(sym)
                total_asset += price * qty
            except:
                pass

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
