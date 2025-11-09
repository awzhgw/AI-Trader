"""
pytest 配置文件
用于配置测试环境和标记
"""
import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)


def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line(
        "markers", "real_connection: 标记需要真实连接的测试"
    )
    config.addinivalue_line(
        "markers", "skip_trade: 标记跳过买卖操作的测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试项，自动添加标记"""
    skip_trade = os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true"

    for item in items:
        # 如果测试名称包含 trade、buy、sell，且 SKIP_TRADE_TESTS=true，则跳过
        if skip_trade and any(keyword in item.name.lower() for keyword in ["trade", "buy", "sell"]):
            # 检查是否已经有 skipif 标记
            has_skipif = any(mark.name == "skipif" for mark in item.iter_markers())
            if not has_skipif:
                item.add_marker(pytest.mark.skipif(
                    True,
                    reason="跳过买卖操作测试以避免真实交易"
                ))
