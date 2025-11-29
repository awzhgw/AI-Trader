"""
AI持仓管理器
记录AI的所有交易，维护独立的AI持仓列表，保护人工持仓
"""
import os
import json
import fcntl
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime


class AIPositionManager:
    """AI持仓管理器"""

    def __init__(self, broker_type: str, account_id: str = "default"):
        """
        Args:
            broker_type: "gjzj" | "futu"
            account_id: 账户ID
        """
        self.broker_type = broker_type
        self.account_id = account_id
        self.position_file = self._get_position_file_path()
        self._ensure_position_file_exists()
        self._position_cache: Optional[Dict[str, int]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 5.0  # 缓存有效期（秒）

    def _get_position_file_path(self) -> Path:
        """获取持仓记录文件路径"""
        project_root = Path(__file__).resolve().parent.parent
        position_dir = project_root / "data" / "ai_positions"
        position_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.broker_type}_ai_positions.jsonl"
        return position_dir / filename

    def _ensure_position_file_exists(self):
        """确保持仓文件存在"""
        if not self.position_file.exists():
            self.position_file.touch()

    def _get_file_lock(self):
        """获取文件锁"""
        class _Lock:
            def __init__(self, lock_path: Path):
                self.lock_path = lock_path.parent / f".{lock_path.name}.lock"
                self._fh = None

            def __enter__(self):
                self._fh = open(self.lock_path, "a+")
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
                return self

            def __exit__(self, exc_type, exc, tb):
                if self._fh:
                    try:
                        fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                    finally:
                        self._fh.close()

        return _Lock(self.position_file)

    def _get_today_date(self) -> str:
        """获取当前交易日期"""
        from tools.general_tools import get_config_value
        today_date = get_config_value("TODAY_DATE")
        if not today_date:
            # 如果没有设置，使用当前日期
            today_date = datetime.now().strftime("%Y-%m-%d")
        return today_date

    def record_buy(
        self,
        symbol: str,
        amount: int,
        price: float,
        total_position: int
    ):
        """
        记录AI买入

        Args:
            symbol: 股票代码
            amount: 买入数量
            price: 买入价格
            total_position: 券商账户总持仓（包含人工持仓）
        """
        today_date = self._get_today_date()

        # 获取当前AI持仓
        current_ai_position = self.get_ai_position(symbol)
        new_ai_position = current_ai_position + amount

        # 记录交易
        record = {
            "date": today_date,
            "action": "buy",
            "symbol": symbol,
            "amount": amount,
            "price": price,
            "ai_position": new_ai_position,
            "total_position": total_position,
            "account_id": self.account_id,
        }

        # 使用文件锁写入
        with self._get_file_lock():
            with open(self.position_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 清除缓存
        self._invalidate_cache()

    def record_sell(
        self,
        symbol: str,
        amount: int,
        price: float,
        total_position: int
    ):
        """
        记录AI卖出

        Args:
            symbol: 股票代码
            amount: 卖出数量
            price: 卖出价格
            total_position: 券商账户总持仓（卖出后）
        """
        today_date = self._get_today_date()

        # 获取当前AI持仓
        current_ai_position = self.get_ai_position(symbol)
        new_ai_position = max(0, current_ai_position - amount)

        # 记录交易
        record = {
            "date": today_date,
            "action": "sell",
            "symbol": symbol,
            "amount": amount,
            "price": price,
            "ai_position": new_ai_position,
            "total_position": total_position,
            "account_id": self.account_id,
        }

        # 使用文件锁写入
        with self._get_file_lock():
            with open(self.position_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 清除缓存
        self._invalidate_cache()

    def get_ai_position(self, symbol: str) -> int:
        """
        获取AI持仓数量

        Args:
            symbol: 股票代码

        Returns:
            AI持仓数量
        """
        all_positions = self.get_all_ai_positions()
        return all_positions.get(symbol, 0)

    def _invalidate_cache(self):
        """使缓存失效"""
        self._position_cache = None
        self._cache_timestamp = None

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._position_cache is None or self._cache_timestamp is None:
            return False

        import time
        return (time.time() - self._cache_timestamp) < self._cache_ttl

    def get_all_ai_positions(self) -> Dict[str, int]:
        """
        获取所有AI持仓（带缓存）

        Returns:
            {symbol: quantity} 字典
        """
        # 检查缓存
        if self._is_cache_valid():
            return self._position_cache.copy()

        positions = {}

        if not self.position_file.exists():
            self._position_cache = positions
            import time
            self._cache_timestamp = time.time()
            return positions

        # 使用文件锁读取
        with self._get_file_lock():
            # 读取所有记录，取每个symbol的最新AI持仓
            with open(self.position_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        # 只处理当前账户的记录
                        if record.get("account_id") != self.account_id:
                            continue

                        symbol = record.get("symbol")
                        ai_position = record.get("ai_position", 0)
                        if symbol:
                            # 更新为最新的持仓（后面的记录会覆盖前面的）
                            positions[symbol] = ai_position
                    except (json.JSONDecodeError, KeyError) as e:
                        # 记录错误但继续处理
                        continue

        # 更新缓存
        self._position_cache = positions
        import time
        self._cache_timestamp = time.time()
        return positions

    def can_sell(self, symbol: str, amount: int) -> Tuple[bool, str]:
        """
        检查是否可以卖出（保护人工持仓）

        Args:
            symbol: 股票代码
            amount: 想要卖出的数量

        Returns:
            (是否可以卖出, 原因说明)
        """
        ai_position = self.get_ai_position(symbol)

        if ai_position < amount:
            return False, f"AI持仓不足：AI持仓={ai_position}, 需要卖出={amount}"

        # 检查是否在保护列表中（可选）
        if self._is_protected(symbol):
            return False, f"{symbol}在保护列表中，禁止AI卖出"

        return True, "可以卖出"

    def _is_protected(self, symbol: str) -> bool:
        """
        检查股票是否在保护列表中

        Args:
            symbol: 股票代码

        Returns:
            是否在保护列表中
        """
        from tools.general_tools import get_config_value

        protected_file = get_config_value("PROTECTED_POSITIONS_FILE")
        if not protected_file:
            return False

        protected_file_path = Path(protected_file)
        if not protected_file_path.exists():
            return False

        try:
            with open(protected_file_path, "r", encoding="utf-8") as f:
                protected_data = json.load(f)

            broker_protected = protected_data.get(self.broker_type, {})
            return symbol in broker_protected
        except (json.JSONDecodeError, KeyError):
            return False

    def get_position_history(self, symbol: Optional[str] = None) -> list:
        """
        获取持仓历史记录

        Args:
            symbol: 股票代码，如果为None则返回所有记录

        Returns:
            记录列表
        """
        history = []

        if not self.position_file.exists():
            return history

        with open(self.position_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get("account_id") != self.account_id:
                        continue

                    if symbol is None or record.get("symbol") == symbol:
                        history.append(record)
                except (json.JSONDecodeError, KeyError):
                    continue

        return history
