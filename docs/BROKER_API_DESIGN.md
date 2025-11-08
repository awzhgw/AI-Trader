# 多券商API集成设计文档（保护人工持仓版）

## 📋 目录
1. [概述](#概述)
2. [核心需求：保护人工持仓](#核心需求保护人工持仓)
3. [架构设计](#架构设计)
4. [持仓隔离机制](#持仓隔离机制)
5. [接口抽象层](#接口抽象层)
6. [实现层设计](#实现层设计)
7. [环境变量配置](#环境变量配置)
8. [实施计划](#实施计划)

---

## 概述

### 目标
设计并实现一个统一的多券商交易接口系统，支持：
- **XtQuant API**（迅投XtQuant A股量化交易）
- **Futu API**（富途证券美股量化交易）
- **模拟交易模式**（现有功能，向后兼容）

**核心要求：保护用户人工持仓，AI只操作自己买入的股票。**

### 核心原则
1. **保护人工持仓**：AI不能卖出用户手动买入的股票
2. **AI持仓追踪**：记录AI的所有交易，维护独立的AI持仓列表
3. **统一接口**：所有券商通过相同的抽象接口访问
4. **市场自动识别**：根据股票代码自动选择对应市场的券商
5. **环境变量驱动**：通过环境变量配置券商和参数
6. **向后兼容**：保持现有模拟交易功能不变

---

## 核心需求：保护人工持仓

### 问题场景

用户已经在券商账户中手动买入了一些股票：
- **富途账户**：手动买入了 AAPL, MSFT 等
- **国金账户**：手动买入了 600519.SH, 601318.SH 等

**需求：**
- ✅ AI可以买入新股票
- ✅ AI可以卖出**自己买入**的股票
- ❌ AI**不能卖出**用户手动买入的股票
- ✅ AI需要知道总持仓，但交易时只考虑AI持仓部分

### 解决方案

#### 方案1：AI持仓记录机制（推荐）

**核心思想：**
- 维护一个独立的"AI持仓记录"（本地文件或数据库）
- 记录AI的所有买入和卖出操作
- 交易前检查：只能卖出AI持仓记录中的股票
- 查询持仓时：返回总持仓，但标注哪些是AI持仓

**数据流：**

```
┌─────────────────────────────────────────────┐
│         券商账户（总持仓）                    │
│  - 人工持仓：AAPL(100), MSFT(50)            │
│  - AI持仓：NVDA(20), TSLA(10)               │
└─────────────────────────────────────────────┘
                    │
                    │ 查询
                    ▼
┌─────────────────────────────────────────────┐
│        AI持仓记录（本地文件）                 │
│  - NVDA: 20 (AI买入)                        │
│  - TSLA: 10 (AI买入)                        │
│  - AAPL: 0 (AI未买入，人工持仓)              │
└─────────────────────────────────────────────┘
                    │
                    │ 交易检查
                    ▼
┌─────────────────────────────────────────────┐
│          交易决策                            │
│  ✅ 可以卖出：NVDA, TSLA (AI持仓)           │
│  ❌ 不能卖出：AAPL, MSFT (人工持仓)          │
└─────────────────────────────────────────────┘
```

#### 方案2：持仓保护列表（辅助）

**核心思想：**
- 用户可以手动设置"保护持仓列表"
- AI不能卖出保护列表中的股票
- 作为额外的安全机制

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     交易工具层 (tool_trade.py)              │
│                    buy() / sell() 统一接口                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              交易适配器工厂 (BrokerAdapterFactory)           │
│         根据环境变量和市场类型创建对应的适配器                │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PtradeAdapter│ │ FutuAdapter │ │ MockAdapter │
│  (A股实盘)   │ │  (美股实盘)  │ │  (模拟交易) │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       │               │               │
       ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│              AI持仓管理器 (AIPositionManager)                │
│  - 记录AI的所有交易                                          │
│  - 维护AI持仓记录                                            │
│  - 交易前检查权限                                            │
└─────────────────────────────────────────────────────────────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Ptrade API  │ │  Futu API   │ │  JSONL文件  │
└─────────────┘ └─────────────┘ └─────────────┘
```

### 目录结构

```
AI-Trader/
├── brokers/                          # 券商适配器目录
│   ├── __init__.py
│   ├── base_broker.py               # 抽象基类
│   ├── broker_factory.py            # 工厂类
│   ├── ai_position_manager.py       # AI持仓管理器（新增）
│   ├── ptrade/                      # Ptrade适配器
│   │   ├── __init__.py
│   │   ├── ptrade_adapter.py
│   │   └── ptrade_client.py
│   ├── futu/                        # Futu适配er
│   │   ├── __init__.py
│   │   ├── futu_adapter.py
│   │   └── futu_client.py
│   └── mock/                        # 模拟交易适配器
│       ├── __init__.py
│       └── mock_adapter.py
├── data/
│   ├── agent_data/                  # 模拟交易数据（现有）
│   └── ai_positions/                # AI持仓记录（新增）
│       ├── ptrade_ai_positions.jsonl
│       └── futu_ai_positions.jsonl
└── agent_tools/
    └── tool_trade.py                # 修改：使用适配器工厂
```

---

## 持仓隔离机制

### AI持仓管理器（AIPositionManager）

**职责：**
1. 记录AI的所有买入和卖出操作
2. 维护AI持仓记录（每个券商独立）
3. 交易前检查：是否可以卖出
4. 查询时：返回总持仓和AI持仓

**数据格式：**

```json
// data/ai_positions/ptrade_ai_positions.jsonl
{
  "date": "2025-01-15",
  "action": "buy",
  "symbol": "600519.SH",
  "amount": 100,
  "price": 1800.0,
  "ai_position": 100,  // AI持仓数量
  "total_position": 500  // 券商账户总持仓（包含人工持仓）
}

// data/ai_positions/futu_ai_positions.jsonl
{
  "date": "2025-01-15",
  "action": "buy",
  "symbol": "NVDA",
  "amount": 10,
  "price": 500.0,
  "ai_position": 10,
  "total_position": 110  // 总持仓：AI(10) + 人工(100)
}
```

**核心方法：**

```python
class AIPositionManager:
    """AI持仓管理器"""

    def __init__(self, broker_type: str, account_id: str):
        """
        Args:
            broker_type: "ptrade" | "futu" | "mock"
            account_id: 账户ID
        """
        self.broker_type = broker_type
        self.account_id = account_id
        self.position_file = self._get_position_file_path()

    def record_buy(self, symbol: str, amount: int, price: float, total_position: int):
        """记录AI买入"""
        # 1. 从券商API获取总持仓
        # 2. 计算AI持仓 = 当前AI持仓 + 买入数量
        # 3. 记录到文件
        pass

    def record_sell(self, symbol: str, amount: int, price: float, total_position: int):
        """记录AI卖出"""
        # 1. 检查AI持仓是否足够
        # 2. 更新AI持仓 = 当前AI持仓 - 卖出数量
        # 3. 记录到文件
        pass

    def get_ai_position(self, symbol: str) -> int:
        """获取AI持仓数量"""
        # 从文件中读取AI持仓记录
        # 返回该股票的AI持仓数量
        pass

    def can_sell(self, symbol: str, amount: int) -> tuple[bool, str]:
        """
        检查是否可以卖出

        Returns:
            (是否可以卖出, 原因说明)
        """
        ai_position = self.get_ai_position(symbol)

        if ai_position < amount:
            return False, f"AI持仓不足：AI持仓={ai_position}, 需要卖出={amount}"

        return True, "可以卖出"

    def get_all_ai_positions(self) -> Dict[str, int]:
        """获取所有AI持仓"""
        # 从文件中读取所有AI持仓
        pass
```

### 交易流程（保护人工持仓）

#### 买入流程

```
1. AI调用 buy("NVDA", 10)
   │
   ▼
2. 创建适配器（FutuAdapter）
   │
   ▼
3. 调用券商API买入
   │
   ▼
4. 查询券商账户总持仓
   │
   ▼
5. 记录到AI持仓管理器
   - AI持仓 += 10
   - 总持仓 = 券商账户持仓
   │
   ▼
6. 返回成功
```

#### 卖出流程（关键：保护人工持仓）

```
1. AI调用 sell("AAPL", 50)
   │
   ▼
2. 创建适配器（FutuAdapter）
   │
   ▼
3. 查询券商账户总持仓
   - 总持仓 = 150 (包含人工持仓100)
   │
   ▼
4. 查询AI持仓管理器
   - AI持仓 = 50
   │
   ▼
5. 检查是否可以卖出
   - can_sell("AAPL", 50) → (True, "可以卖出")
   │
   ▼
6. 调用券商API卖出
   │
   ▼
7. 更新AI持仓管理器
   - AI持仓 = 50 - 50 = 0
   - 总持仓 = 150 - 50 = 100 (剩余人工持仓)
   │
   ▼
8. 返回成功
```

#### 卖出保护示例

```
场景：用户手动买入AAPL(100)，AI买入AAPL(50)

总持仓：150
AI持仓：50
人工持仓：100

AI尝试卖出60股：
  ❌ 失败：AI持仓不足（只有50股）

AI尝试卖出50股：
  ✅ 成功：卖出AI持仓的50股
  剩余：人工持仓100股（不受影响）
```

### 持仓保护列表（可选增强）

用户可以手动设置保护列表，额外保护某些股票：

```python
# configs/protected_positions.json
{
  "ptrade": {
    "600519.SH": "人工持仓，禁止AI卖出",
    "601318.SH": "人工持仓，禁止AI卖出"
  },
  "futu": {
    "AAPL": "人工持仓，禁止AI卖出",
    "MSFT": "人工持仓，禁止AI卖出"
  }
}
```

**检查逻辑：**

```python
def can_sell(self, symbol: str, amount: int) -> tuple[bool, str]:
    # 1. 检查AI持仓是否足够
    ai_position = self.get_ai_position(symbol)
    if ai_position < amount:
        return False, f"AI持仓不足：{ai_position} < {amount}"

    # 2. 检查是否在保护列表中（额外保护）
    if self._is_protected(symbol):
        return False, f"{symbol}在保护列表中，禁止AI卖出"

    return True, "可以卖出"
```

---

## 接口抽象层

### BaseBroker 抽象基类

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple

class BaseBroker(ABC):
    """券商适配器抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_id = config.get("account_id", "default")
        self.broker_type = self._get_broker_type()

        # 初始化AI持仓管理器
        from brokers.ai_position_manager import AIPositionManager
        self.ai_position_manager = AIPositionManager(
            broker_type=self.broker_type,
            account_id=self.account_id
        )

    @abstractmethod
    def connect(self) -> bool:
        """连接到券商API"""
        pass

    @abstractmethod
    def buy(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """
        买入股票

        流程：
        1. 调用券商API买入
        2. 查询总持仓
        3. 记录到AI持仓管理器
        """
        pass

    @abstractmethod
    def sell(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """
        卖出股票（保护人工持仓）

        流程：
        1. 查询总持仓
        2. 查询AI持仓
        3. 检查是否可以卖出（AI持仓是否足够）
        4. 如果可以，调用券商API卖出
        5. 更新AI持仓管理器
        """
        pass

    @abstractmethod
    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        获取持仓信息

        Returns:
            {
                "total_positions": {symbol: quantity},  # 总持仓（包含人工）
                "ai_positions": {symbol: quantity},     # AI持仓
                "manual_positions": {symbol: quantity},  # 人工持仓（计算得出）
                "cash": float,
                "total_asset": float
            }
        """
        pass

    def _check_sell_permission(self, symbol: str, amount: int) -> Tuple[bool, str]:
        """
        检查是否可以卖出（保护人工持仓）

        Returns:
            (是否可以卖出, 原因说明)
        """
        return self.ai_position_manager.can_sell(symbol, amount)
```

---

## 实现层设计

### PtradeAdapter 实现示例

```python
class PtradeAdapter(BaseBroker):
    """Ptrade适配器（A股）"""

    def sell(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """卖出股票（保护人工持仓）"""

        # 1. 查询券商账户总持仓
        total_positions = self._fetch_total_positions()
        total_qty = total_positions.get(symbol, 0)

        # 2. 查询AI持仓
        ai_qty = self.ai_position_manager.get_ai_position(symbol)

        # 3. 检查是否可以卖出
        can_sell, reason = self._check_sell_permission(symbol, amount)
        if not can_sell:
            return {
                "success": False,
                "error": reason,
                "symbol": symbol,
                "amount": amount,
                "ai_position": ai_qty,
                "total_position": total_qty,
                "manual_position": total_qty - ai_qty
            }

        # 4. 调用Ptrade API卖出
        try:
            from ptrade import order, order_market

            if order_type == OrderType.MARKET:
                result = order_market(symbol, -amount)  # 负数表示卖出
            else:
                result = order(symbol, -amount, price)

            # 5. 更新AI持仓管理器
            new_total_qty = total_qty - amount
            self.ai_position_manager.record_sell(
                symbol=symbol,
                amount=amount,
                price=price or self.get_price(symbol),
                total_position=new_total_qty
            )

            return {
                "success": True,
                "order_id": result.get("order_id", ""),
                "message": f"卖出成功，AI持仓剩余: {ai_qty - amount}",
                "ai_position": ai_qty - amount,
                "total_position": new_total_qty
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Ptrade卖出失败: {str(e)}"
            }

    def buy(
        self,
        symbol: str,
        amount: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET
    ) -> Dict[str, Any]:
        """买入股票"""

        # 1. 调用Ptrade API买入
        try:
            from ptrade import order, order_market

            if order_type == OrderType.MARKET:
                result = order_market(symbol, amount)
            else:
                result = order(symbol, amount, price)

            # 2. 查询总持仓
            total_positions = self._fetch_total_positions()
            total_qty = total_positions.get(symbol, 0)

            # 3. 记录到AI持仓管理器
            self.ai_position_manager.record_buy(
                symbol=symbol,
                amount=amount,
                price=price or self.get_price(symbol),
                total_position=total_qty
            )

            return {
                "success": True,
                "order_id": result.get("order_id", ""),
                "message": "买入成功",
                "ai_position": self.ai_position_manager.get_ai_position(symbol),
                "total_position": total_qty
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Ptrade买入失败: {str(e)}"
            }

    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取持仓（区分总持仓和AI持仓）"""

        # 1. 从券商API获取总持仓
        total_positions = self._fetch_total_positions()

        # 2. 从AI持仓管理器获取AI持仓
        ai_positions = self.ai_position_manager.get_all_ai_positions()

        # 3. 计算人工持仓
        manual_positions = {}
        for sym, total_qty in total_positions.items():
            ai_qty = ai_positions.get(sym, 0)
            manual_qty = total_qty - ai_qty
            if manual_qty > 0:
                manual_positions[sym] = manual_qty

        # 4. 获取账户信息
        account_info = self._fetch_account_info()

        result = {
            "total_positions": total_positions,
            "ai_positions": ai_positions,
            "manual_positions": manual_positions,
            "cash": account_info.get("cash", 0.0),
            "total_asset": account_info.get("total_asset", 0.0)
        }

        # 如果指定了symbol，只返回该股票的信息
        if symbol:
            return {
                "symbol": symbol,
                "total_position": total_positions.get(symbol, 0),
                "ai_position": ai_positions.get(symbol, 0),
                "manual_position": manual_positions.get(symbol, 0)
            }

        return result
```

### FutuAdapter 实现示例

类似PtradeAdapter，但使用Futu API：

```python
class FutuAdapter(BaseBroker):
    """Futu适配器（美股）"""

    def sell(self, symbol: str, amount: int, ...) -> Dict[str, Any]:
        """卖出股票（保护人工持仓）"""
        # 1. 查询总持仓和AI持仓
        # 2. 检查是否可以卖出
        # 3. 调用Futu API卖出
        # 4. 更新AI持仓管理器
        pass
```

---

## 环境变量配置

### .env 配置示例

```bash
# ============================================
# 券商配置
# ============================================

# 交易模式: "mock" | "ptrade" | "futu" | "auto"
BROKER_MODE=auto

# ============================================
# Ptrade配置（A股）
# ============================================
PTRADE_ENABLED=true
PTRADE_ACCOUNT_ID=your_account_id
PTRADE_TRADE_NAME=your_trade_name

# ============================================
# Futu配置（美股）
# ============================================
FUTU_ENABLED=true
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
FUTU_MARKET=US
FUTU_SECURITY_FIRM=your_security_firm
FUTU_REAL_TRADE=false

# ============================================
# AI持仓保护配置
# ============================================
# 是否启用持仓保护（默认true）
ENABLE_POSITION_PROTECTION=true

# 保护持仓列表文件路径（可选）
PROTECTED_POSITIONS_FILE=configs/protected_positions.json
```

---

## 实施计划

### 阶段1：AI持仓管理器（1周）

1. **实现AIPositionManager**
   - 持仓记录文件格式设计
   - 买入/卖出记录方法
   - 持仓查询方法
   - 卖出权限检查方法

2. **测试持仓管理器**
   - 单元测试
   - 边界情况测试

### 阶段2：适配器改造（1-2周）

1. **修改BaseBroker**
   - 集成AIPositionManager
   - 添加卖出权限检查

2. **修改PtradeAdapter**
   - 买入时记录AI持仓
   - 卖出前检查AI持仓
   - 查询时区分总持仓和AI持仓

3. **修改FutuAdapter**
   - 同上

### 阶段3：测试与验证（1周）

1. **功能测试**
   - 买入新股票
   - 卖出AI持仓
   - 尝试卖出人工持仓（应该失败）

2. **边界测试**
   - AI持仓为0时尝试卖出
   - 部分卖出AI持仓
   - 混合持仓场景

---

## 总结

本设计通过**AI持仓管理器**机制，确保：

1. ✅ **保护人工持仓**：AI只能卖出自己买入的股票
2. ✅ **完整记录**：记录AI的所有交易操作
3. ✅ **清晰区分**：查询时区分总持仓、AI持仓、人工持仓
4. ✅ **向后兼容**：模拟交易模式不受影响

**关键机制：**
- AI持仓管理器维护独立的AI持仓记录
- 卖出前检查AI持仓是否足够
- 查询时返回总持仓和AI持仓的区分

---

**文档版本**: v2.0
**最后更新**: 2025-01-XX
**作者**: AI-Trader Development Team
