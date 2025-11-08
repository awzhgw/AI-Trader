#!/usr/bin/env python
"""
运行所有broker单测的脚本

使用方法:
    python tests/brokers/run_tests.py
    或者
    pytest tests/brokers/ -v
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pytest
except ImportError:
    print("❌ 请先安装pytest: pip install pytest pytest-mock")
    sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 开始运行Broker单测...")
    print("=" * 60)

    # 运行所有测试
    test_dir = Path(__file__).parent
    exit_code = pytest.main([
        str(test_dir),
        "-v",  # 详细输出
        "--tb=short",  # 简短的traceback
        "-s",  # 显示print输出
        "--color=yes",  # 彩色输出
    ])

    print("=" * 60)
    if exit_code == 0:
        print("✅ 所有测试通过！")
    else:
        print(f"❌ 测试失败，退出码: {exit_code}")
    print("=" * 60)

    sys.exit(exit_code)
