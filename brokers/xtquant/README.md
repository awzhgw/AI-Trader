# XtQuant适配器使用说明

## 概述

XtQuant适配器基于迅投XtQuant交易模块，用于A股量化交易。XtQuant提供了完整的交易API，支持同步和异步下单、查询持仓、查询资产等功能。

**参考文档**: https://dict.thinktrader.net/nativeApi/xttrader.html

## 安装

```bash
pip install xtquant
```

## 使用示例

### 基本使用

```python
from brokers.xtquant.xtquant_adapter import XtQuantAdapter
from brokers.broker_factory import BrokerAdapterFactory

# 创建适配器
broker = BrokerAdapterFactory.create_broker(broker_mode="xtquant")

# 连接（必需）
if broker.connect():
    print("连接成功")

    # 买入股票
    result = broker.buy("600519.SH", 100)
    if result["success"]:
        print(f"买入成功: {result['message']}")
        print(f"订单ID: {result['order_id']}")
    else:
        print(f"买入失败: {result['error']}")

    # 卖出股票（会自动保护人工持仓）
    result = broker.sell("600519.SH", 50)
    if result["success"]:
        print(f"卖出成功: {result['message']}")
    else:
        print(f"卖出失败: {result['error']}")

    # 获取持仓
    position = broker.get_position()
    print(f"总持仓: {position['total_positions']}")
    print(f"AI持仓: {position['ai_positions']}")
    print(f"人工持仓: {position['manual_positions']}")
else:
    print("连接失败")
```

### 使用环境变量配置

```python
import os
from brokers.broker_factory import BrokerAdapterFactory

# 设置环境变量
os.environ["XTQUANT_ACCOUNT_ID"] = "your_account_id"
os.environ["XTQUANT_SESSION_ID"] = "0"

# 创建适配器
broker = BrokerAdapterFactory.create_broker(broker_mode="xtquant")

# 连接并交易
broker.connect()
result = broker.buy("600519.SH", 100)
```

## 配置参数

### 环境变量

```bash
# XtQuant配置
XTQUANT_ACCOUNT_ID=your_account_id
XTQUANT_SESSION_ID=0  # 会话ID，0表示默认会话
```

### 配置字典

```python
config = {
    "account_id": "your_account_id",  # 账户ID（必需）
    "session_id": 0,                  # 会话ID（可选，默认0）
    "trader": None                    # XtQuantTrader实例（可选，会自动创建）
}
```

## API说明

### 连接

```python
broker.connect() -> bool
```

建立与XtQuant交易系统的连接。必须在交易前调用。

### 买入

```python
broker.buy(symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict
```

- `symbol`: 股票代码，如 "600519.SH"
- `amount`: 买入数量，A股必须是100的倍数
- `price`: 限价单价格（限价单时必需）
- `order_type`: 订单类型，`OrderType.MARKET`（市价）或 `OrderType.LIMIT`（限价）

### 卖出

```python
broker.sell(symbol: str, amount: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> Dict
```

- 会自动保护人工持仓，只能卖出AI买入的股票
- 其他参数同买入

### 获取持仓

```python
broker.get_position(symbol: Optional[str] = None) -> Dict
```

返回持仓信息，包括：
- `total_positions`: 总持仓（包含人工持仓）
- `ai_positions`: AI持仓
- `manual_positions`: 人工持仓
- `cash`: 现金
- `total_asset`: 总资产

## 保护人工持仓

XtQuant适配器会自动保护人工持仓：

- ✅ AI只能卖出自己买入的股票
- ✅ 卖出前会检查AI持仓是否足够
- ✅ 查询持仓时会区分总持仓、AI持仓、人工持仓

## 注意事项

1. **必须先连接**：使用前必须调用`connect()`方法
2. **A股规则**：A股必须100股的倍数交易
3. **同步下单**：当前实现使用同步下单，下单会阻塞直到返回结果
4. **价格获取**：优先使用本地数据，实际使用时可以通过XtData模块获取实时价格
5. **持仓查询**：持仓查询功能需要根据实际XtQuant API调整

## 故障排查

### 问题：连接失败，提示"未安装XtQuant模块"

**解决方案**：安装XtQuant模块
```bash
pip install xtquant
```

### 问题：下单失败，提示"XtQuant未连接"

**解决方案**：确保在交易前调用了`connect()`方法
```python
broker = XtQuantAdapter(config)
broker.connect()  # 必需！
result = broker.buy("600519.SH", 100)
```

### 问题：买入失败，提示"order_id=0"

**解决方案**：检查账户ID是否正确，账户是否有足够资金

## 参考文档

- [XtQuant交易模块文档](https://dict.thinktrader.net/nativeApi/xttrader.html)
- [XtQuant完整实例](https://dict.thinktrader.net/nativeApi/xttrader.html#%E5%AE%8C%E6%95%B4%E5%AE%9E%E4%BE%8B)
