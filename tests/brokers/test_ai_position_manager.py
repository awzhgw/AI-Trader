"""
AI持仓管理器单测
"""
import pytest
from brokers.ai_position_manager import AIPositionManager

@pytest.fixture
def manager():
    """提供一个干净的 AIPositionManager 实例"""
    broker_type = "test_broker"
    account_id = "test_account"
    mgr = AIPositionManager(broker_type, account_id)
    
    # Setup: 确保文件不存在
    if mgr.position_file.exists():
        mgr.position_file.unlink()
        
    yield mgr
    
    # Teardown: 清理文件
    if mgr.position_file.exists():
        mgr.position_file.unlink()

def test_init(manager):
    """测试初始化"""
    assert manager.broker_type == "test_broker"
    assert manager.account_id == "test_account"
    assert manager.position_file.parent.exists()

def test_record_buy(manager):
    """测试记录买入"""
    manager.record_buy("AAPL", 10, 150.0, 10)
    assert manager.get_ai_position("AAPL") == 10
    
    manager.record_buy("AAPL", 5, 155.0, 15)
    assert manager.get_ai_position("AAPL") == 15

def test_record_sell(manager):
    """测试记录卖出"""
    manager.record_buy("AAPL", 10, 150.0, 10)
    manager.record_sell("AAPL", 5, 160.0, 5)
    assert manager.get_ai_position("AAPL") == 5

def test_record_sell_insufficient(manager):
    """测试卖出数量超过持仓"""
    manager.record_buy("AAPL", 10, 150.0, 10)
    # 卖出超过持仓的数量（允许但归零）
    manager.record_sell("AAPL", 15, 160.0, 0)
    assert manager.get_ai_position("AAPL") == 0

def test_get_all_ai_positions(manager):
    """测试获取所有AI持仓"""
    manager.record_buy("AAPL", 10, 150.0, 10)
    manager.record_buy("MSFT", 5, 300.0, 5)
    manager.record_buy("NVDA", 3, 500.0, 3)
    
    positions = manager.get_all_ai_positions()
    assert positions == {"AAPL": 10, "MSFT": 5, "NVDA": 3}

@pytest.mark.parametrize("setup_qty, sell_qty, expected_can, expected_msg_part", [
    (10, 5, True, "可以卖出"),
    (10, 15, False, "AI持仓不足"),
    (0, 5, False, "AI持仓不足"),
])
def test_can_sell(manager, setup_qty, sell_qty, expected_can, expected_msg_part):
    """测试卖出检查逻辑"""
    if setup_qty > 0:
        manager.record_buy("AAPL", setup_qty, 150.0, setup_qty)
        
    can_sell, reason = manager.can_sell("AAPL", sell_qty)
    assert can_sell is expected_can
    assert expected_msg_part in reason

def test_get_position_history(manager):
    """测试获取持仓历史"""
    manager.record_buy("AAPL", 10, 150.0, 10)
    manager.record_sell("AAPL", 5, 160.0, 5)
    manager.record_buy("MSFT", 5, 300.0, 5)
    
    history = manager.get_position_history("AAPL")
    assert len(history) == 2
    assert history[0]["action"] == "buy"
    assert history[1]["action"] == "sell"

def test_multiple_accounts(manager):
    """测试多个账户隔离"""
    # manager 是 account "test_account"
    manager1 = manager
    manager2 = AIPositionManager("test_broker", "account2")
    
    # Ensure manager2 is clean
    if manager2.position_file.exists():
        manager2.position_file.unlink()
    
    try:
        manager1.record_buy("AAPL", 10, 150.0, 10)
        assert manager2.get_ai_position("AAPL") == 0
        
        manager2.record_buy("AAPL", 5, 150.0, 5)
        assert manager2.get_ai_position("AAPL") == 5
    finally:
        if manager2.position_file.exists():
            manager2.position_file.unlink()
