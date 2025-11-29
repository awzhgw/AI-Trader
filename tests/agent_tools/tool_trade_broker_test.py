import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from agent_tools.tool_trade import buy, sell

@pytest.fixture
def mock_dependencies():
    with patch('agent_tools.tool_trade.get_config_value') as mock_config, \
         patch('agent_tools.tool_trade.get_latest_position') as mock_position, \
         patch('agent_tools.tool_trade.get_open_prices') as mock_prices, \
         patch('agent_tools.tool_trade.BrokerAdapterFactory') as mock_factory, \
         patch('agent_tools.tool_trade._position_lock') as mock_lock, \
         patch('builtins.open', new_callable=MagicMock) as mock_open:
        
        # Setup default config
        def config_side_effect(key, default=None):
            if key == "SIGNATURE": return "test_agent"
            if key == "TODAY_DATE": return "2023-01-01"
            if key == "LOG_PATH": return "./data/agent_data"
            if key == "BROKER_MODE": return None # Default to simulation
            return default
        mock_config.side_effect = config_side_effect
        
        # Setup default position
        # CASH: 100000, AAPL: 100
        mock_position.return_value = ({"CASH": 100000, "AAPL": 100}, 1)
        
        # Setup default prices
        mock_prices.return_value = {"AAPL_price": 100.0}
        
        # Setup lock context manager
        mock_lock.return_value.__enter__.return_value = None
        
        yield {
            "config": mock_config,
            "position": mock_position,
            "prices": mock_prices,
            "factory": mock_factory,
            "open": mock_open
        }

def get_callable(tool):
    if hasattr(tool, "fn"):
        return tool.fn
    if hasattr(tool, "__wrapped__"):
        return tool.__wrapped__
    return tool

def test_buy_simulation_mode(mock_dependencies):
    # Default config is simulation (BROKER_MODE=None)
    buy_fn = get_callable(buy)
    result = buy_fn("AAPL", 10)
    
    # Verify broker factory NOT called
    mock_dependencies["factory"].create_broker.assert_not_called()
    
    # Verify result success (position updated)
    assert result["AAPL"] == 110
    assert result["CASH"] == 99000.0 # 100000 - 10 * 100

def test_buy_broker_mode_success(mock_dependencies):
    # Enable broker mode
    def config_side_effect(key, default=None):
        if key == "BROKER_MODE": return "gjzj"
        if key == "SIGNATURE": return "test_agent"
        if key == "TODAY_DATE": return "2023-01-01"
        return default
    mock_dependencies["config"].side_effect = config_side_effect
    
    # Setup mock broker
    mock_broker = MagicMock()
    mock_broker.buy.return_value = {"success": True} # Success result
    mock_dependencies["factory"].create_broker.return_value = mock_broker
    
    buy_fn = get_callable(buy)
    result = buy_fn("AAPL", 10)
    
    # Verify broker called
    mock_dependencies["factory"].create_broker.assert_called_with(symbol="AAPL", broker_mode="gjzj")
    mock_broker.buy.assert_called_once()
    
    # Verify result success (local position updated)
    assert result["AAPL"] == 110

def test_buy_broker_mode_failure(mock_dependencies):
    # Enable broker mode
    def config_side_effect(key, default=None):
        if key == "BROKER_MODE": return "gjzj"
        if key == "SIGNATURE": return "test_agent"
        if key == "TODAY_DATE": return "2023-01-01"
        return default
    mock_dependencies["config"].side_effect = config_side_effect
    
    # Setup mock broker to fail
    mock_broker = MagicMock()
    mock_broker.buy.return_value = {"error": "Broker error"}
    mock_dependencies["factory"].create_broker.return_value = mock_broker
    
    buy_fn = get_callable(buy)
    result = buy_fn("AAPL", 10)
    
    # Verify broker called
    mock_broker.buy.assert_called_once()
    
    # Verify result is error
    assert "error" in result
    assert "Broker buy failed" in result["error"]
    
    # Verify local position NOT updated
    # Check that open() was not called with 'a' mode (except maybe by _position_lock if it wasn't mocked properly, but it is)
    # Since we mocked _position_lock, the only open('...', 'a') call would be the write.
    write_calls = [call for call in mock_dependencies["open"].mock_calls if 'a' in call.args or (len(call.args)>1 and call.args[1]=='a')]
    assert len(write_calls) == 0

def test_sell_broker_mode_success(mock_dependencies):
    # Enable broker mode
    def config_side_effect(key, default=None):
        if key == "BROKER_MODE": return "futu"
        if key == "SIGNATURE": return "test_agent"
        if key == "TODAY_DATE": return "2023-01-01"
        return default
    mock_dependencies["config"].side_effect = config_side_effect
    
    # Setup mock broker
    mock_broker = MagicMock()
    mock_broker.sell.return_value = {"success": True}
    mock_dependencies["factory"].create_broker.return_value = mock_broker
    
    # Need to mock _get_today_buy_amount for T+1 check in sell
    # But since we are testing US stock (AAPL), T+1 check is skipped or different?
    # Code: if market == "cn": ...
    # AAPL is US.
    
    sell_fn = get_callable(sell)
    result = sell_fn("AAPL", 10)
    
    # Verify broker called
    mock_dependencies["factory"].create_broker.assert_called_with(symbol="AAPL", broker_mode="futu")
    mock_broker.sell.assert_called_once()
    
    # Verify result success (local position updated)
    assert result["AAPL"] == 90 # 100 - 10

def test_sell_broker_mode_failure(mock_dependencies):
    # Enable broker mode
    def config_side_effect(key, default=None):
        if key == "BROKER_MODE": return "futu"
        if key == "SIGNATURE": return "test_agent"
        if key == "TODAY_DATE": return "2023-01-01"
        return default
    mock_dependencies["config"].side_effect = config_side_effect
    
    # Setup mock broker to fail
    mock_broker = MagicMock()
    mock_broker.sell.return_value = {"error": "Broker error"}
    mock_dependencies["factory"].create_broker.return_value = mock_broker
    
    sell_fn = get_callable(sell)
    result = sell_fn("AAPL", 10)
    
    # Verify broker called
    mock_broker.sell.assert_called_once()
    
    # Verify result is error
    assert "error" in result
    assert "Broker sell failed" in result["error"]
