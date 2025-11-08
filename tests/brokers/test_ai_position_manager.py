"""
AI持仓管理器单测
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest

from brokers.ai_position_manager import AIPositionManager


class TestAIPositionManager:
    """AI持仓管理器测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.test_broker_type = "test_broker"
        self.test_account_id = "test_account"

        # 设置环境变量，让AIPositionManager使用临时目录
        self.original_project_root = None

    def teardown_method(self):
        """每个测试方法后执行"""
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """测试初始化"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)
        assert manager.broker_type == self.test_broker_type
        assert manager.account_id == self.test_account_id
        assert manager.position_file.exists()

    def test_record_buy(self):
        """测试记录买入"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 记录买入
        manager.record_buy("AAPL", 10, 150.0, 10)

        # 检查AI持仓
        ai_position = manager.get_ai_position("AAPL")
        assert ai_position == 10

        # 再次买入
        manager.record_buy("AAPL", 5, 155.0, 15)
        ai_position = manager.get_ai_position("AAPL")
        assert ai_position == 15

    def test_record_sell(self):
        """测试记录卖出"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 先买入
        manager.record_buy("AAPL", 10, 150.0, 10)

        # 卖出
        manager.record_sell("AAPL", 5, 160.0, 5)

        # 检查AI持仓
        ai_position = manager.get_ai_position("AAPL")
        assert ai_position == 5

    def test_record_sell_insufficient(self):
        """测试卖出数量超过持仓"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 先买入
        manager.record_buy("AAPL", 10, 150.0, 10)

        # 卖出超过持仓的数量（应该允许，但持仓不能为负）
        manager.record_sell("AAPL", 15, 160.0, 0)

        # 检查AI持仓（应该为0，不能为负）
        ai_position = manager.get_ai_position("AAPL")
        assert ai_position == 0

    def test_get_all_ai_positions(self):
        """测试获取所有AI持仓"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 买入多只股票
        manager.record_buy("AAPL", 10, 150.0, 10)
        manager.record_buy("MSFT", 5, 300.0, 5)
        manager.record_buy("NVDA", 3, 500.0, 3)

        # 获取所有持仓
        all_positions = manager.get_all_ai_positions()

        assert all_positions["AAPL"] == 10
        assert all_positions["MSFT"] == 5
        assert all_positions["NVDA"] == 3

    def test_can_sell_sufficient(self):
        """测试可以卖出（持仓足够）"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 买入
        manager.record_buy("AAPL", 10, 150.0, 10)

        # 检查是否可以卖出
        can_sell, reason = manager.can_sell("AAPL", 5)
        assert can_sell is True
        assert "可以卖出" in reason

    def test_can_sell_insufficient(self):
        """测试不能卖出（持仓不足）"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 买入
        manager.record_buy("AAPL", 10, 150.0, 10)

        # 检查是否可以卖出超过持仓的数量
        can_sell, reason = manager.can_sell("AAPL", 15)
        assert can_sell is False
        assert "AI持仓不足" in reason

    def test_can_sell_no_position(self):
        """测试不能卖出（没有持仓）"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 检查没有持仓的股票
        can_sell, reason = manager.can_sell("AAPL", 5)
        assert can_sell is False
        assert "AI持仓不足" in reason

    def test_get_position_history(self):
        """测试获取持仓历史"""
        manager = AIPositionManager(self.test_broker_type, self.test_account_id)

        # 记录多笔交易
        manager.record_buy("AAPL", 10, 150.0, 10)
        manager.record_sell("AAPL", 5, 160.0, 5)
        manager.record_buy("MSFT", 5, 300.0, 5)

        # 获取历史
        history = manager.get_position_history("AAPL")
        assert len(history) == 2  # 一笔买入，一笔卖出

        # 检查历史记录内容
        assert history[0]["action"] == "buy"
        assert history[1]["action"] == "sell"

    def test_multiple_accounts(self):
        """测试多个账户隔离"""
        manager1 = AIPositionManager(self.test_broker_type, "account1")
        manager2 = AIPositionManager(self.test_broker_type, "account2")

        # account1买入
        manager1.record_buy("AAPL", 10, 150.0, 10)

        # account2不应该看到account1的持仓
        ai_position = manager2.get_ai_position("AAPL")
        assert ai_position == 0

        # account2买入
        manager2.record_buy("AAPL", 5, 150.0, 5)
        ai_position = manager2.get_ai_position("AAPL")
        assert ai_position == 5
