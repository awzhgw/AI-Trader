# 多券商API集成设计文档（保护人工持仓版）

## 📋 核心需求

**重要：保护您的人工持仓！**

您已经在券商账户中手动买入了一些股票：
- **富途账户**：手动买入了 AAPL, MSFT 等
- **国金账户**：手动买入了 600519.SH, 601318.SH 等

**需求：**
- ✅ AI可以买入新股票
- ✅ AI可以卖出**自己买入**的股票
- ❌ AI**绝对不能卖出**您手动买入的股票
- ✅ AI需要知道总持仓，但交易时只考虑AI持仓部分

---

## 🛡️ 解决方案：AI持仓管理器

### 核心机制

**维护独立的"AI持仓记录"，只允许AI卖出自己买入的股票。**

### 工作原理

```
┌─────────────────────────────────────────────┐
│         券商账户（总持仓）                    │
│  - 人工持仓：AAPL(100), MSFT(50)            │
│  - AI持仓：NVDA(20), TSLA(10)               │
│  总计：AAPL(100), MSFT(50), NVDA(20), TSLA(10)│
└─────────────────────────────────────────────┘
                    │
                    │ 查询
                    ▼
┌─────────────────────────────────────────────┐
│        AI持仓记录（本地文件）                 │
│  - NVDA: 20 (AI买入)                        │
│  - TSLA: 10 (AI买入)                        │
│  - AAPL: 0 (AI未买入，只有人工持仓)          │
│  - MSFT: 0 (AI未买入，只有人工持仓)          │
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

### 数据存储

AI持仓记录存储在独立文件中：

```
data/
└── ai_positions/
    ├── ptrade_ai_positions.jsonl  # 国金AI持仓记录
    └── futu_ai_positions.jsonl    # 富途AI持仓记录
```

**记录格式：**

```json
{
  "date": "2025-01-15",
  "action": "buy",
  "symbol": "NVDA",
  "amount": 10,
  "price": 500.0,
  "ai_position": 10,      // AI持仓数量
  "total_position": 110    // 券商账户总持仓（AI 10 + 人工 100）
}
```

---

## 🔄 交易流程

### 买入流程

```
1. AI调用 buy("NVDA", 10)
   │
   ▼
2. 调用券商API买入
   │
   ▼
3. 查询券商账户总持仓
   │
   ▼
4. 记录到AI持仓管理器
   - AI持仓 += 10
   │
   ▼
5. 返回成功
```

### 卖出流程（关键：保护人工持仓）

```
1. AI调用 sell("AAPL", 50)
   │
   ▼
2. 查询券商账户总持仓
   - 总持仓 = 150 (包含人工持仓100)
   │
   ▼
3. 查询AI持仓记录
   - AI持仓 = 50
   │
   ▼
4. 检查是否可以卖出
   - AI持仓(50) >= 卖出数量(50) ✅
   │
   ▼
5. 调用券商API卖出
   │
   ▼
6. 更新AI持仓记录
   - AI持仓 = 50 - 50 = 0
   │
   ▼
7. 返回成功
```

### 卖出保护示例

**场景：**
- 您手动买入：AAPL(100股)
- AI买入：AAPL(50股)
- 总持仓：150股

**AI尝试卖出60股：**
```
❌ 失败：AI持仓不足
   原因：AI持仓(50) < 卖出数量(60)
   您的100股人工持仓不受影响
```

**AI尝试卖出50股：**
```
✅ 成功：卖出AI持仓的50股
   剩余：您的100股人工持仓（完全不受影响）
```

---

## 📊 持仓查询

### 查询结果格式

```python
get_position("AAPL")
# 返回：
{
    "symbol": "AAPL",
    "total_position": 150,      # 总持仓（券商账户）
    "ai_position": 50,          # AI持仓
    "manual_position": 100      # 人工持仓（计算得出）
}

get_position()  # 查询所有
# 返回：
{
    "total_positions": {
        "AAPL": 150,
        "MSFT": 50,
        "NVDA": 20
    },
    "ai_positions": {
        "AAPL": 50,
        "NVDA": 20
    },
    "manual_positions": {
        "AAPL": 100,
        "MSFT": 50
    }
}
```

---

## 🏗️ 架构设计

### 核心组件

```
┌─────────────────────────────────────┐
│     交易工具 (tool_trade.py)        │
│     buy() / sell()                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   券商适配器 (Ptrade/Futu)          │
│   - 调用券商API                      │
│   - 集成AI持仓管理器                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   AI持仓管理器 (AIPositionManager)  │
│   - 记录AI交易                       │
│   - 维护AI持仓记录                   │
│   - 检查卖出权限                     │
└─────────────────────────────────────┘
```

### AI持仓管理器功能

```python
class AIPositionManager:
    """AI持仓管理器"""

    def record_buy(symbol, amount, price, total_position):
        """记录AI买入"""
        # AI持仓 += amount
        # 写入文件

    def record_sell(symbol, amount, price, total_position):
        """记录AI卖出"""
        # 检查AI持仓是否足够
        # AI持仓 -= amount
        # 写入文件

    def get_ai_position(symbol):
        """获取AI持仓数量"""
        # 从文件读取

    def can_sell(symbol, amount):
        """检查是否可以卖出"""
        # 返回 (是否可以, 原因)
        # 如果AI持仓 < amount，返回False
```

---

## ⚙️ 环境变量配置

```bash
# 券商模式
BROKER_MODE=auto  # mock | ptrade | futu | auto

# Ptrade配置
PTRADE_ENABLED=true
PTRADE_ACCOUNT_ID=your_account_id

# Futu配置
FUTU_ENABLED=true
FUTU_HOST=127.0.0.1
FUTU_PORT=11111

# AI持仓保护（默认启用）
ENABLE_POSITION_PROTECTION=true
```

---

## 📝 使用示例

### 示例1：AI买入新股票

```python
# AI买入NVDA（您没有持仓）
buy("NVDA", 10)

# 结果：
# ✅ 成功买入
# ✅ AI持仓记录：NVDA = 10
# ✅ 您的其他持仓不受影响
```

### 示例2：AI买入已有股票

```python
# 您已经手动买入AAPL(100)
# AI再买入AAPL(50)

buy("AAPL", 50)

# 结果：
# ✅ 成功买入
# ✅ 券商账户总持仓：150（您的100 + AI的50）
# ✅ AI持仓记录：AAPL = 50
# ✅ 您的100股不受影响
```

### 示例3：AI卖出自己买入的股票

```python
# AI持仓：NVDA(10)
# 您没有NVDA持仓

sell("NVDA", 10)

# 结果：
# ✅ 成功卖出
# ✅ AI持仓记录：NVDA = 0
# ✅ 您的持仓不受影响
```

### 示例4：AI尝试卖出人工持仓（被阻止）

```python
# 您手动买入：AAPL(100)
# AI买入：AAPL(50)
# 总持仓：150

# AI尝试卖出60股
sell("AAPL", 60)

# 结果：
# ❌ 失败：AI持仓不足
#    错误信息：AI持仓(50) < 卖出数量(60)
# ✅ 您的100股完全不受影响
```

### 示例5：AI部分卖出

```python
# AI持仓：NVDA(20)
# 您没有NVDA持仓

# AI卖出10股
sell("NVDA", 10)

# 结果：
# ✅ 成功卖出10股
# ✅ AI持仓记录：NVDA = 10（剩余10股）
# ✅ 您的持仓不受影响
```

---

## 🛡️ 安全保证

### 保护机制

1. **AI持仓记录**
   - ✅ 独立文件存储AI持仓
   - ✅ 每次交易都更新记录
   - ✅ 卖出前检查AI持仓

2. **卖出权限检查**
   - ✅ 卖出前必须检查AI持仓
   - ✅ AI持仓不足时拒绝卖出
   - ✅ 返回清晰的错误信息

3. **持仓查询**
   - ✅ 区分总持仓、AI持仓、人工持仓
   - ✅ 清晰显示哪些是AI持仓

### 安全清单

- ✅ AI只能卖出自己买入的股票
- ✅ AI不能卖出人工持仓
- ✅ AI持仓记录独立存储
- ✅ 每次交易都更新记录
- ✅ 卖出前强制检查权限

---

## 🔍 验证方法

### 验证AI持仓保护

```python
# 1. 查看AI持仓记录
from brokers.ai_position_manager import AIPositionManager

manager = AIPositionManager("futu", "your_account_id")
ai_positions = manager.get_all_ai_positions()
print(f"AI持仓: {ai_positions}")

# 2. 尝试卖出人工持仓（应该失败）
result = sell("AAPL", 100)  # 假设您有100股人工持仓
assert result["success"] == False
assert "AI持仓不足" in result["error"]

# 3. 查看总持仓和AI持仓
position = get_position("AAPL")
print(f"总持仓: {position['total_position']}")
print(f"AI持仓: {position['ai_position']}")
print(f"人工持仓: {position['manual_position']}")
```

---

## 📚 实施步骤

### 阶段1：AI持仓管理器（1周）
1. 实现AIPositionManager类
2. 设计持仓记录文件格式
3. 实现买入/卖出记录方法
4. 实现权限检查方法

### 阶段2：适配器改造（1-2周）
1. 在BaseBroker中集成AIPositionManager
2. 修改PtradeAdapter和FutuAdapter
3. 买入时记录AI持仓
4. 卖出前检查AI持仓

### 阶段3：测试验证（1周）
1. 测试买入新股票
2. 测试卖出AI持仓
3. 测试卖出人工持仓（应该失败）
4. 测试混合持仓场景

---

## ✅ 总结

通过**AI持仓管理器**机制，确保：

1. ✅ **保护人工持仓**：AI只能卖出自己买入的股票
2. ✅ **完整记录**：记录AI的所有交易操作
3. ✅ **清晰区分**：查询时区分总持仓、AI持仓、人工持仓
4. ✅ **安全可靠**：卖出前强制检查权限

**您的 manually买入的股票将完全受到保护！**

---

**文档版本**: v2.0
**最后更新**: 2025-01-XX
