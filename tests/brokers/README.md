# Broker单测说明

## 概述

本测试套件支持两种测试模式：
1. **真实连接测试**：使用真实的国金证券（GJZJ）和富途证券（Futu）连接进行测试
2. **模拟测试**：使用 mock 对象进行单元测试

**重要提示**：真实连接测试默认跳过买卖操作，以避免真实交易。如需测试买卖功能，请设置环境变量 `SKIP_TRADE_TESTS=false`。

## 环境配置

### 1. 安装依赖

```bash
pip install pytest pytest-mock python-dotenv
```

### 2. 配置环境变量

在项目根目录的 `.env` 文件中配置以下变量：

#### 国金证券（GJZJ）配置
```bash
# Gjzj配置（A股）
GJZJ_ACCOUNT_ID="your_account_id"
GJZJ_SESSION_ID="0"  # 会话ID，0表示默认会话
GJZJ_STRATEGY_NAME="AI-Trader"
GJZJ_PATH="D:\\迅投极速交易终端 睿智融科版\\userdata_mini"  # MiniQMT客户端路径（必需）
```

#### 富途证券（Futu）配置
```bash
# Futu配置（美股）
FUTU_ACCOUNT_ID="your_account_id"
FUTU_HOST="127.0.0.1"
FUTU_PORT="11111"
FUTU_MARKET="US"
FUTU_SECURITY_FIRM="your_security_firm"
FUTU_REAL_TRADE="false"
```

#### 测试控制配置
```bash
# 是否跳过买卖操作测试（默认：true，跳过买卖以避免真实交易）
SKIP_TRADE_TESTS="true"  # 设置为 "false" 以启用买卖测试（谨慎使用！）
```

## 运行测试

### 方式1：使用pytest直接运行

```bash
# 运行所有broker测试
pytest tests/brokers/ -v

# 运行特定测试文件
pytest tests/brokers/test_ai_position_manager.py -v
pytest tests/brokers/test_mock_adapter.py -v
pytest tests/brokers/test_broker_factory.py -v
pytest tests/brokers/test_gjzj_adapter.py -v
pytest tests/brokers/test_futu_adapter.py -v

# 运行特定测试类
pytest tests/brokers/test_gjzj_adapter.py::TestGjzjAdapterReal -v

# 运行特定测试方法
pytest tests/brokers/test_gjzj_adapter.py::TestGjzjAdapterReal::test_connect -v

# 只运行真实连接测试（跳过买卖）
pytest tests/brokers/ -v -m "not skip_trade"

# 运行所有测试（包括买卖操作，谨慎使用！）
SKIP_TRADE_TESTS=false pytest tests/brokers/ -v
```

### 方式2：使用run_tests.py脚本

```bash
python tests/brokers/run_tests.py
```

## 测试覆盖

### test_ai_position_manager.py
- ✅ 初始化测试
- ✅ 记录买入
- ✅ 记录卖出
- ✅ 获取AI持仓
- ✅ 卖出权限检查（保护人工持仓）
- ✅ 多账户隔离

### test_mock_adapter.py
- ✅ 买入成功
- ✅ 买入失败（现金不足）
- ✅ 卖出成功
- ✅ 卖出保护人工持仓
- ✅ 获取持仓（区分总持仓、AI持仓、人工持仓）
- ✅ A股必须100的倍数

### test_broker_factory.py
- ✅ 市场识别（A股/美股）
- ✅ 创建Mock适配器
- ✅ 自动模式创建适配器
- ✅ 获取券商配置

### test_gjzj_adapter.py（真实连接测试）
- ✅ 初始化（从 .env 读取配置）
- ✅ 真实连接测试
- ✅ 获取价格（使用本地数据）
- ✅ 获取持仓信息（真实数据）
- ✅ 获取账户信息（真实数据）
- ✅ 买入验证（A股必须100的倍数）
- ⚠️ 买入操作（默认跳过，需设置 SKIP_TRADE_TESTS=false）
- ⚠️ 卖出操作（默认跳过，需设置 SKIP_TRADE_TESTS=false）
- ⚠️ 卖出保护人工持仓（默认跳过，需设置 SKIP_TRADE_TESTS=false）

### test_futu_adapter.py（真实连接测试）
- ✅ 初始化（从 .env 读取配置）
- ✅ 连接测试（目前是模拟实现）
- ✅ 获取价格（使用本地数据）
- ✅ 获取持仓信息
- ✅ 获取账户信息
- ⚠️ 买入操作（默认跳过，需设置 SKIP_TRADE_TESTS=false）
- ⚠️ 卖出操作（默认跳过，需设置 SKIP_TRADE_TESTS=false）

## 真实连接测试说明

### 国金证券（GJZJ）测试

1. **前置条件**：
   - 已安装 `xtquant` 模块：`pip install xtquant`
   - 已配置 `GJZJ_PATH` 环境变量，指向 MiniQMT 客户端的 `userdata_mini` 目录
   - MiniQMT 客户端已启动并登录

2. **测试内容**：
   - 连接测试：验证能否成功连接到国金证券交易系统
   - 持仓查询：获取真实账户持仓信息
   - 账户信息：获取真实账户资金信息
   - 价格获取：使用本地数据获取股票价格

3. **注意事项**：
   - 默认跳过买卖操作，避免真实交易
   - 如果连接失败，相关测试会自动跳过
   - 确保账户有足够的权限进行查询操作

### 富途证券（Futu）测试

1. **前置条件**：
   - 已安装 `futu` 模块：`pip install futu`
   - 已配置富途 API 相关环境变量
   - 富途 OpenD 已启动并登录

2. **测试内容**：
   - 连接测试：验证能否成功连接到富途 API
   - 持仓查询：获取真实账户持仓信息（如果已实现）
   - 账户信息：获取真实账户资金信息（如果已实现）
   - 价格获取：使用本地数据获取股票价格

3. **注意事项**：
   - FutuAdapter 目前是模拟实现，部分功能可能返回默认值
   - 默认跳过买卖操作，避免真实交易

## 测试标记

### pytest 标记

- `@pytest.mark.skipif(SKIP_TRADE_TESTS, ...)`：跳过买卖操作测试
- `@pytest.mark.real_connection`：标记需要真实连接的测试

### 环境变量控制

- `SKIP_TRADE_TESTS`：控制是否跳过买卖操作测试
  - `"true"`（默认）：跳过买卖操作
  - `"false"`：启用买卖操作测试（谨慎使用！）

## 注意事项

1. **真实交易风险**：
   - 默认情况下，所有买卖操作测试都会被跳过
   - 如需测试买卖功能，请明确设置 `SKIP_TRADE_TESTS=false`
   - 测试买卖功能时，请确保使用测试账户，避免真实资金损失

2. **环境依赖**：
   - 真实连接测试需要相应的交易软件已启动并登录
   - 如果连接失败，相关测试会自动跳过，不会导致测试失败

3. **数据隔离**：
   - 测试会创建临时文件记录AI持仓
   - 测试结束后会自动清理临时文件

4. **网络连接**：
   - 真实连接测试需要网络连接
   - 如果网络不稳定，可能导致测试失败或跳过

5. **账户权限**：
   - 确保测试账户有足够的权限进行查询操作
   - 查询操作不会影响账户资金和持仓

## 故障排查

### 问题：连接失败

**解决方案**：
1. 检查 `.env` 文件中的配置是否正确
2. 确保交易软件已启动并登录
3. 检查网络连接是否正常
4. 查看测试输出中的错误信息

### 问题：无法获取价格数据

**解决方案**：
1. 检查本地数据文件是否存在
2. 确认股票代码格式正确（A股：`600519.SH`，美股：`AAPL`）
3. 检查 `TODAY_DATE` 环境变量是否设置

### 问题：测试被跳过

**解决方案**：
1. 检查环境变量配置
2. 查看测试输出中的跳过原因
3. 确保所有前置条件已满足

## 示例输出

```bash
$ pytest tests/brokers/test_gjzj_adapter.py -v

tests/brokers/test_gjzj_adapter.py::TestGjzjAdapterReal::test_init PASSED
tests/brokers/test_gjzj_adapter.py::TestGjzjAdapterReal::test_connect PASSED
tests/brokers/test_gjzj_adapter.py::test_get_price PASSED
tests/brokers/test_gjzj_adapter.py::test_get_position PASSED
tests/brokers/test_gjzj_adapter.py::test_buy_validation PASSED
tests/brokers/test_gjzj_adapter.py::test_buy_not_connected SKIPPED [1] (跳过买卖操作测试以避免真实交易)
tests/brokers/test_gjzj_adapter.py::test_sell_validation SKIPPED [1] (跳过买卖操作测试以避免真实交易)
```

## 相关文档

- [Gjzj适配器使用说明](../../brokers/gjzj/README.md)
- [Futu适配器使用说明](../../brokers/futu/README.md)
- [Broker API设计文档](../../docs/BROKER_API_DESIGN.md)
