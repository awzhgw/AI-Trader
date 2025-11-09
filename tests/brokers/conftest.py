"""
pytest 配置文件
用于配置测试环境和标记
"""
# 必须在导入任何其他模块之前设置警告过滤
# 这些警告来自富途库内部使用的已弃用protobuf API，在模块导入时就会产生
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.simplefilter("ignore", DeprecationWarning)

import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)


def pytest_configure(config):
    """配置 pytest 标记和警告过滤"""
    # 配置 pytest 标记
    config.addinivalue_line(
        "markers", "real_connection: 标记需要真实连接的测试"
    )
    config.addinivalue_line(
        "markers", "skip_trade: 标记跳过买卖操作的测试"
    )

    # 在 pytest 配置中也设置警告过滤
    config.option.disable_warnings = True
    # 添加警告过滤到 pytest 配置
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)


def pytest_collection_modifyitems(config, items):
    """修改测试项，自动添加标记"""
    skip_trade = os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true"

    # 定义应该跳过的测试名称模式（实际执行交易的测试）
    # 不包括：record_buy/record_sell（记录操作）、can_sell（检查函数）等
    trade_test_patterns = [
        "buy_success",
        "buy_insufficient",
        "sell_success",
        "sell_protect",
        "buy_not_connected",
        "buy_validation",  # 虽然只是验证，但会调用buy()方法
        "sell_validation",  # 虽然只是验证，但会调用sell()方法
    ]

    for item in items:
        # 如果测试名称匹配交易操作模式，且 SKIP_TRADE_TESTS=true，则跳过
        if skip_trade:
            # 检查是否匹配交易操作模式
            is_trade_test = any(pattern in item.name.lower() for pattern in trade_test_patterns)

            # 检查是否已经有 skipif 标记
            has_skipif = any(mark.name == "skipif" for mark in item.iter_markers())

            # 如果是交易测试且还没有skipif标记，则添加跳过标记
            if is_trade_test and not has_skipif:
                item.add_marker(pytest.mark.skipif(
                    True,
                    reason="跳过买卖操作测试以避免真实交易"
                ))
