# Broker单测说明

## 运行测试

### 方式1：使用pytest直接运行

```bash
# 运行所有broker测试
pytest tests/brokers/ -v

# 运行特定测试文件
pytest tests/brokers/test_ai_position_manager.py -v
pytest tests/brokers/test_mock_adapter.py -v
pytest tests/brokers/test_broker_factory.py -v
pytest tests/brokers/test_xtquant_adapter.py -v
pytest tests/brokers/test_futu_adapter.py -v

# 运行特定测试类
pytest tests/brokers/test_ai_position_manager.py::TestAIPositionManager -v

# 运行特定测试方法
pytest tests/brokers/test_ai_position_manager.py::TestAIPositionManager::test_record_buy -v
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

### test_xtquant_adapter.py
- ✅ 初始化
- ✅ 连接成功/失败
- ✅ 获取价格
- ✅ A股买入（必须100的倍数）
- ✅ 买入失败（未连接）
- ✅ 卖出保护人工持仓

### test_futu_adapter.py
- ✅ 初始化
- ✅ 连接
- ✅ 获取价格
- ✅ 买入成功
- ✅ 卖出保护人工持仓

## 注意事项

1. **Mock测试**：MockAdapter的测试需要mock `get_config_value`、`get_open_prices`、`get_latest_position`等函数
2. **环境变量**：某些测试会设置临时环境变量，测试结束后会自动清理
3. **临时文件**：测试会创建临时目录和文件，测试结束后会自动清理
4. **依赖**：需要安装pytest：`pip install pytest`

## 安装依赖

```bash
pip install pytest pytest-mock
```
