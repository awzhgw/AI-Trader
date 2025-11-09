"""
GjzjAdapter单测
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)

from brokers.gjzj.gjzj_adapter import GjzjAdapter
from brokers.base_broker import OrderType


class TestGjzjAdapter:
    """GjzjAdapter测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        # 从 .env 读取配置，如果没有则使用默认值
        account_id = os.getenv("GJZJ_ACCOUNT_ID", "test_account")
        session_id = int(os.getenv("GJZJ_SESSION_ID", "0"))

        self.config = {
            "account_id": account_id,
            "session_id": session_id,
            "path": "/test/path/userdata_mini"  # 测试用的path
        }
        # 清理测试文件，确保测试隔离
        self._cleanup_test_files()

    def teardown_method(self):
        """每个测试方法后执行"""
        # 清理测试文件
        self._cleanup_test_files()

    def _cleanup_test_files(self):
        """清理测试文件"""
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        position_dir = project_root / "data" / "ai_positions"
        ai_position_file = position_dir / "gjzj_ai_positions.jsonl"
        if ai_position_file.exists():
            ai_position_file.unlink()

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    def test_init(self, mock_get_config):
        """测试初始化"""
        mock_get_config.return_value = "2025-01-15"

        adapter = GjzjAdapter(self.config)
        assert adapter.broker_type == "gjzj"
        assert adapter.account_id == "test_account"
        assert adapter.session_id == 0

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    @patch('xtquant.xttype', create=True)
    @patch('xtquant.xttrader', create=True)
    def test_connect_success(self, mock_xttrader_module, mock_xttype_module, mock_get_config):
        """测试连接成功"""
        mock_get_config.return_value = "2025-01-15"

        # Mock StockAccount
        mock_xttype_module.StockAccount = MagicMock()
        mock_xttype_module.StockAccount.STOCK_ACCOUNT = 1

        # Mock XtQuantTrader
        mock_trader_instance = MagicMock()
        mock_trader_instance.start.return_value = None  # start()不返回值
        mock_trader_instance.connect.return_value = 0  # connect()返回0表示成功
        mock_xttrader_module.XtQuantTrader = MagicMock(return_value=mock_trader_instance)

        adapter = GjzjAdapter(self.config)
        result = adapter.connect()

        assert result is True
        assert adapter._connected is True
        assert adapter.trader is not None

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    @patch('builtins.print')  # 抑制警告输出
    def test_connect_import_error(self, mock_print, mock_get_config):
        """测试连接失败（模块未安装）"""
        mock_get_config.return_value = "2025-01-15"

        # 使用patch来模拟导入xtquant时抛出ImportError
        import builtins
        import sys

        # 保存原始的__import__
        original_import = builtins.__import__

        # 临时移除xtquant相关模块（如果存在），确保重新导入时会触发ImportError
        xtquant_modules = {}
        for key in list(sys.modules.keys()):
            if key.startswith('xtquant'):
                xtquant_modules[key] = sys.modules.pop(key)

        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'xtquant' or (isinstance(name, str) and name.startswith('xtquant')):
                raise ImportError("No module named 'xtquant'")
            # 对于其他模块，使用真实的导入
            return original_import(name, globals, locals, fromlist, level)

        try:
            # 临时替换__import__
            builtins.__import__ = mock_import

            adapter = GjzjAdapter(self.config)
            result = adapter.connect()
            assert result is False

            # 验证警告信息被打印
            assert mock_print.called
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("未安装XtQuant模块" in str(call) for call in print_calls)
        finally:
            # 恢复原始__import__
            builtins.__import__ = original_import
            # 恢复sys.modules
            sys.modules.update(xtquant_modules)

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    @patch('tools.price_tools.get_open_prices')
    def test_get_price(self, mock_get_prices, mock_get_config):
        """测试获取价格"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"600519.SH_price": 1800.0}

        adapter = GjzjAdapter(self.config)
        price = adapter.get_price("600519.SH")
        assert price == 1800.0

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    def test_buy_cn_lot_size(self, mock_get_config):
        """测试A股买入必须100的倍数"""
        mock_get_config.return_value = "2025-01-15"

        adapter = GjzjAdapter(self.config)
        result = adapter.buy("600519.SH", 50)  # 不是100的倍数

        assert result["success"] is False
        assert "multiples of 100" in result["error"]

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    def test_buy_not_connected(self, mock_get_config):
        """测试买入失败（未连接）"""
        mock_get_config.return_value = "2025-01-15"

        adapter = GjzjAdapter(self.config)
        result = adapter.buy("600519.SH", 100)

        assert result["success"] is False
        assert "未连接" in result["error"]

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    @patch('tools.price_tools.get_open_prices')
    @patch('xtquant.xttype', create=True)
    @patch('xtquant.xttrader', create=True)
    def test_buy_success(self, mock_xttrader_module, mock_xttype_module, mock_get_prices, mock_get_config):
        """测试买入成功"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"600519.SH_price": 1800.0}

        # Mock StockAccount
        mock_account = MagicMock()
        mock_account.account_id = "test_account"
        mock_account.account_type = 1
        mock_xttype_module.StockAccount = MagicMock(return_value=mock_account)

        # Mock XtQuantTrader
        mock_trader_instance = MagicMock()
        mock_trader_instance.start.return_value = None
        mock_trader_instance.connect.return_value = 0  # connect()返回0表示成功
        mock_trader_instance.order_stock.return_value = 12345  # order_id
        mock_trader_instance.query_stock_positions.return_value = []
        mock_xttrader_module.XtQuantTrader = MagicMock(return_value=mock_trader_instance)

        adapter = GjzjAdapter(self.config)
        adapter.connect()
        result = adapter.buy("600519.SH", 100)
        assert result["success"] is True
        assert result["symbol"] == "600519.SH"
        assert result["amount"] == 100

    @patch('brokers.gjzj.gjzj_adapter.get_config_value')
    @patch('tools.price_tools.get_open_prices')
    @patch('xtquant.xttype', create=True)
    @patch('xtquant.xttrader', create=True)
    def test_sell_protect_manual_position(self, mock_xttrader_module, mock_xttype_module, mock_get_prices, mock_get_config):
        """测试卖出保护人工持仓"""
        mock_get_config.return_value = "2025-01-15"
        mock_get_prices.return_value = {"600519.SH_price": 1800.0}

        # Mock StockAccount
        mock_account = MagicMock()
        mock_account.account_id = "test_account"
        mock_account.account_type = 1
        mock_xttype_module.StockAccount = MagicMock(return_value=mock_account)

        # Mock XtQuantTrader
        mock_trader_instance = MagicMock()
        mock_trader_instance.start.return_value = None
        mock_trader_instance.connect.return_value = 0  # connect()返回0表示成功
        mock_trader_instance.order_stock.return_value = 12345
        mock_trader_instance.query_stock_positions.return_value = []
        mock_xttrader_module.XtQuantTrader = MagicMock(return_value=mock_trader_instance)

        adapter = GjzjAdapter(self.config)
        adapter.connect()

        # AI买入100股
        adapter.buy("600519.SH", 100)

        # 尝试卖出200股（应该失败，因为AI只有100股）
        result = adapter.sell("600519.SH", 200)

        assert result["success"] is False
        assert "AI持仓不足" in result["error"]
