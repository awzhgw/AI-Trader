# 多券商API集成系统

## 概述

本系统实现了统一的多券商交易接口，支持：
- **Gjzj API**（基于迅投XtQuant A股量化交易）
- **Futu API**（富途证券美股量化交易）

**核心特性：保护用户人工持仓，AI只操作自己买入的股票。**

## 目录结构

```
brokers/
├── __init__.py
├── base_broker.py              # 抽象基类
├── broker_factory.py            # 工厂类
├── ai_position_manager.py       # AI持仓管理器
├── gjzj/                        # Gjzj适配器
│   ├── __init__.py
│   └── gjzj_adapter.py
└── futu/                        # Futu适配器
    ├── __init__.py
    └── futu_adapter.py
```

## 核心组件

### 1. AIPositionManager（AI持仓管理器）

记录AI的所有交易，维护独立的AI持仓列表，保护人工持仓。

**主要方法：**
- `record_buy()`: 记录AI买入
- `record_sell()`: 记录AI卖出
- `get_ai_position()`: 获取AI持仓数量
- `can_sell()`: 检查是否可以卖出（保护人工持仓）

### 2. BaseBroker（抽象基类）

所有券商适配器的基类，定义了统一的接口。

**主要方法：**
- `buy()`: 买入股票
- `sell()`: 卖出股票（保护人工持仓）
- `get_position()`: 获取持仓信息
- `connect()`: 连接到券商API

### 3. BrokerAdapterFactory（工厂类）

根据环境变量和市场类型自动创建对应的适配器。

**主要方法：**
- `create_broker()`: 创建券商适配器
- `detect_market()`: 根据股票代码识别市场（A股/美股）

### 4. GjzjAdapter（A股适配器）

Gjzj API的适配器，用于A股交易。基于迅投XtQuant交易模块。
参考文档: https://dict.thinktrader.net/nativeApi/xttrader.html

### 5. FutuAdapter（美股适配器）

Futu API的适配器，用于美股交易。

## 使用示例

### 基本使用

```python
from brokers.broker_factory import BrokerAdapterFactory

# 自动识别市场并创建适配器
broker = BrokerAdapterFactory.create_broker(symbol="AAPL")

# 买入
result = broker.buy("AAPL", 10)
print(result)

# 卖出（会自动保护人工持仓）
result = broker.sell("AAPL", 5)
print(result)

# 获取持仓
position = broker.get_position()
print(f"总持仓: {position['total_positions']}")
print(f"AI持仓: {position['ai_positions']}")
print(f"人工持仓: {position['manual_positions']}")
```

### 指定券商模式

```python
# 使用Gjzj模式（A股）
broker = BrokerAdapterFactory.create_broker(broker_mode="gjzj")

# 使用Futu模式（美股）
broker = BrokerAdapterFactory.create_broker(broker_mode="futu")

# 自动模式（根据symbol自动选择）
broker = BrokerAdapterFactory.create_broker(symbol="600519.SH", broker_mode="auto")
```

## 环境变量配置

```bash
# 交易模式: "gjzj" | "futu" | "auto"
BROKER_MODE=auto

# Gjzj配置（A股）
GJZJ_ENABLED=true
GJZJ_ACCOUNT_ID=your_account_id
GJZJ_SESSION_ID=0  # 会话ID，0表示默认会话

# Futu配置（美股）
FUTU_ENABLED=true
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
FUTU_MARKET=US
FUTU_SECURITY_FIRM=your_security_firm
FUTU_REAL_TRADE=false

# AI持仓保护配置
ENABLE_POSITION_PROTECTION=true
PROTECTED_POSITIONS_FILE=configs/protected_positions.json
```

## 保护人工持仓机制

### 工作原理

1. **AI持仓记录**：所有AI的交易操作都会记录到 `data/ai_positions/{broker_type}_ai_positions.jsonl`
2. **卖出检查**：卖出前会检查AI持仓是否足够，如果不足则拒绝卖出
3. **持仓区分**：查询持仓时会区分总持仓、AI持仓、人工持仓

### 示例场景

```
场景：用户手动买入AAPL(100股)，AI买入AAPL(50股)

总持仓：150股
AI持仓：50股
人工持仓：100股

AI尝试卖出60股：
  ❌ 失败：AI持仓不足（只有50股）

AI尝试卖出50股：
  ✅ 成功：卖出AI持仓的50股
  剩余：人工持仓100股（不受影响）
```

## 数据文件

### AI持仓记录文件

位置：`data/ai_positions/{broker_type}_ai_positions.jsonl`

格式：
```json
{
  "date": "2025-01-15",
  "action": "buy",
  "symbol": "AAPL",
  "amount": 10,
  "price": 150.0,
  "ai_position": 10,
  "total_position": 110,
  "account_id": "default"
}
```

## 测试

运行单测：

```bash
# 运行所有测试
pytest tests/brokers/ -v

# 运行特定测试
pytest tests/brokers/test_ai_position_manager.py -v
```

详细测试说明请参考：`tests/brokers/README.md`

## 注意事项

1. **Gjzj适配器**：
   - 需要安装XtQuant模块: `pip install xtquant`
   - 需要先调用`connect()`方法建立连接
   - 支持同步和异步下单（当前实现使用同步下单）
   - 参考文档: https://dict.thinktrader.net/nativeApi/xttrader.html

2. **Futu适配器**：目前是框架实现，实际的API调用部分需要根据实际API文档完善
3. **数据隔离**：不同账户的AI持仓记录是隔离的

## 后续开发

1. 完善Gjzj和Futu的实际API调用
2. 添加更多券商支持
3. 添加持仓保护列表功能
4. 添加交易历史查询功能
5. 添加性能监控和日志

