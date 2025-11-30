"""
AI持仓管理器
记录AI的所有交易，维护独立的AI持仓列表，保护人工持仓
"""
import json
import fcntl
import time
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

class AIPositionManager:
    """AI持仓管理器"""

    def __init__(self, broker_type: str, account_id: str = "default"):
        self.broker_type = broker_type
        self.account_id = account_id
        self.position_file = self._get_position_file_path()
        self._ensure_position_file_exists()
        self._position_cache: Optional[Dict[str, int]] = None
        self._cache_timestamp: float = 0
        self._cache_ttl = 5.0

    def _get_position_file_path(self) -> Path:
        """获取持仓记录文件路径"""
        path = Path(__file__).resolve().parent.parent / "data" / "ai_positions" / f"{self.broker_type}_ai_positions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_position_file_exists(self):
        if not self.position_file.exists():
            self.position_file.touch()

    @contextmanager
    def _file_lock(self):
        """文件锁上下文管理器"""
        lock_path = self.position_file.parent / f".{self.position_file.name}.lock"
        with open(lock_path, "a+") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _record_transaction(self, action: str, symbol: str, amount: int, price: float, total_pos: int, new_ai_pos: int):
        """统一记录交易"""
        from tools.general_tools import get_config_value
        today = get_config_value("TODAY_DATE") or datetime.now().strftime("%Y-%m-%d")
        
        record = {
            "date": today,
            "action": action,
            "symbol": symbol,
            "amount": amount,
            "price": price,
            "ai_position": new_ai_pos,
            "total_position": total_pos,
            "account_id": self.account_id,
        }

        with self._file_lock(), open(self.position_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        self._position_cache = None  # Invalidate cache

    def record_buy(self, symbol: str, amount: int, price: float, total_position: int):
        """记录AI买入"""
        new_pos = self.get_ai_position(symbol) + amount
        self._record_transaction("buy", symbol, amount, price, total_position, new_pos)

    def record_sell(self, symbol: str, amount: int, price: float, total_position: int):
        """记录AI卖出"""
        new_pos = max(0, self.get_ai_position(symbol) - amount)
        self._record_transaction("sell", symbol, amount, price, total_position, new_pos)

    def get_ai_position(self, symbol: str) -> int:
        return self.get_all_ai_positions().get(symbol, 0)

    def get_all_ai_positions(self) -> Dict[str, int]:
        """获取所有AI持仓（带缓存）"""
        if self._position_cache is not None and (time.time() - self._cache_timestamp) < self._cache_ttl:
            return self._position_cache.copy()

        positions = {}
        if self.position_file.exists():
            with self._file_lock(), open(self.position_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        rec = json.loads(line)
                        if rec.get("account_id") == self.account_id and (sym := rec.get("symbol")):
                            positions[sym] = rec.get("ai_position", 0)
                    except (json.JSONDecodeError, KeyError): continue

        self._position_cache = positions
        self._cache_timestamp = time.time()
        return positions

    def can_sell(self, symbol: str, amount: int) -> Tuple[bool, str]:
        """检查是否可以卖出"""
        ai_pos = self.get_ai_position(symbol)
        if ai_pos < amount:
            return False, f"AI持仓不足: {ai_pos} < {amount}"
        
        if self._is_protected(symbol):
            return False, f"{symbol}在保护列表中"
            
        return True, "可以卖出"

    def _is_protected(self, symbol: str) -> bool:
        """检查股票是否在保护列表中"""
        from tools.general_tools import get_config_value
        if not (f_path := get_config_value("PROTECTED_POSITIONS_FILE")): return False
        
        path = Path(f_path)
        if not path.exists(): return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return symbol in data.get(self.broker_type, {})
        except Exception: return False

    def get_position_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取持仓历史"""
        if not self.position_file.exists(): return []
        
        history = []
        with open(self.position_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    rec = json.loads(line)
                    if rec.get("account_id") == self.account_id:
                        if symbol is None or rec.get("symbol") == symbol:
                            history.append(rec)
                except Exception: continue
        return history
