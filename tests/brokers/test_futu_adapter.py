"""
FutuAdapter真实连接测试
使用真实的富途证券连接进行测试，但跳过买卖操作以避免真实交易
"""
import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)

from brokers.futu.futu_adapter import FutuAdapter
from brokers.broker_factory import BrokerAdapterFactory


class TestFutuAdapterReal:
    """FutuAdapter真实连接测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试方法前后执行"""
        # 从 .env 读取配置
        self.account_id = os.getenv("FUTU_ACCOUNT_ID", "default")
        self.host = os.getenv("FUTU_HOST", "127.0.0.1")
        self.port = int(os.getenv("FUTU_PORT", "11111"))
        self.market = os.getenv("FUTU_MARKET", "US")
        self.security_firm = os.getenv("FUTU_SECURITY_FIRM", "")
        self.real_trade = os.getenv("FUTU_REAL_TRADE", "false").lower() == "true"

        # 创建适配器
        self.adapter = FutuAdapter.create_from_config()

        # 清理测试文件
        self._cleanup_test_files()

        yield

        # 测试后清理
        self._cleanup_test_files()
        # 断开连接
        if hasattr(self.adapter, '_quote_ctx') and self.adapter._quote_ctx:
            try:
                self.adapter._quote_ctx.close()
            except:
                pass

    def _cleanup_test_files(self):
        """清理测试文件"""
        project_root = Path(__file__).resolve().parent.parent.parent
        position_dir = project_root / "data" / "ai_positions"
        ai_position_file = position_dir / "futu_ai_positions.jsonl"
        if ai_position_file.exists():
            ai_position_file.unlink()

    def test_init(self):
        """测试初始化"""
        assert self.adapter.broker_type == "futu"
        assert self.adapter.account_id == self.account_id
        assert self.adapter.host == self.host
        assert self.adapter.port == self.port
        assert self.adapter.market == self.market
        assert self.adapter.security_firm == self.security_firm
        assert self.adapter.real_trade == self.real_trade

    def test_connect(self):
        """测试连接"""
        result = self.adapter.connect()

        # 注意：FutuAdapter 目前是模拟实现，connect() 总是返回 True
        # 如果未来实现了真实连接，这里会测试真实连接
        assert result is True

        # 如果实现了真实连接，检查连接状态
        if hasattr(self.adapter, '_quote_ctx') and self.adapter._quote_ctx:
            assert self.adapter._quote_ctx is not None

    def test_get_price(self):
        """测试获取价格（使用本地数据）"""
        # 确保已连接
        if not hasattr(self.adapter, '_connected') or not self.adapter._connected:
            self.adapter.connect()

        # 测试获取美股价格（使用本地数据）
        try:
            price = self.adapter.get_price("AAPL")
            assert isinstance(price, (int, float))
            assert price > 0
        except ValueError as e:
            # 如果数据不存在，跳过测试
            pytest.skip(f"无法获取价格数据: {e}")

    def test_get_position(self):
        """测试获取持仓信息"""
        # 确保已连接
        if not hasattr(self.adapter, '_connected') or not self.adapter._connected:
            self.adapter.connect()

        # 获取持仓
        position = self.adapter.get_position()

        assert isinstance(position, dict)
        assert "total_positions" in position
        assert "ai_positions" in position
        assert "manual_positions" in position
        assert "cash" in position
        assert "total_asset" in position

        # 验证数据类型
        assert isinstance(position["total_positions"], dict)
        assert isinstance(position["ai_positions"], dict)
        assert isinstance(position["manual_positions"], dict)
        assert isinstance(position["cash"], (int, float))
        assert isinstance(position["total_asset"], (int, float))

    def test_get_position_by_symbol(self):
        """测试获取指定股票的持仓"""
        # 确保已连接
        if not hasattr(self.adapter, '_connected') or not self.adapter._connected:
            self.adapter.connect()

        # 测试获取指定股票持仓
        test_symbol = "AAPL"
        position = self.adapter.get_position(test_symbol)

        assert isinstance(position, dict)
        assert position["symbol"] == test_symbol
        assert "total_position" in position
        assert "ai_position" in position
        assert "manual_position" in position

        assert isinstance(position["total_position"], int)
        assert isinstance(position["ai_position"], int)
        assert isinstance(position["manual_position"], int)

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_buy_validation(self):
        """测试买入验证（不实际买入）"""
        # 确保已连接
        if not hasattr(self.adapter, '_connected') or not self.adapter._connected:
            self.adapter.connect()

        # 测试买入（目前是模拟实现）
        result = self.adapter.buy("AAPL", 10)
        # 由于是模拟实现，应该总是成功
        # 如果未来实现真实连接，这里会测试真实买入逻辑
        assert isinstance(result, dict)
        assert "success" in result

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_sell_protect_manual_position(self):
        """测试卖出保护人工持仓（不实际卖出）"""
        # 确保已连接
        if not hasattr(self.adapter, '_connected') or not self.adapter._connected:
            self.adapter.connect()

        # 获取当前持仓
        position = self.adapter.get_position("AAPL")
        ai_position = position["ai_position"]

        # 尝试卖出超过AI持仓的数量
        if ai_position > 0:
            result = self.adapter.sell("AAPL", ai_position + 10)
            assert result["success"] is False
            assert "AI持仓不足" in result["error"] or "持仓不足" in result["error"]
        else:
            pytest.skip("当前没有AI持仓，跳过测试")

    def test_fetch_account_info(self):
        """测试获取账户信息"""
        # 确保已连接
        if not hasattr(self.adapter, '_connected') or not self.adapter._connected:
            self.adapter.connect()

        account_info = self.adapter._fetch_account_info()

        assert isinstance(account_info, dict)
        assert "cash" in account_info
        assert "total_asset" in account_info
        assert isinstance(account_info["cash"], (int, float))
        assert isinstance(account_info["total_asset"], (int, float))

        # 注意：目前是模拟实现，返回默认值
        # 如果未来实现真实连接，这里会测试真实账户信息

    def test_fetch_total_positions(self):
        """测试获取总持仓"""
        # 确保已连接
        if not hasattr(self.adapter, '_connected') or not self.adapter._connected:
            self.adapter.connect()

        positions = self.adapter._fetch_total_positions()

        assert isinstance(positions, dict)
        # 验证持仓数据格式
        for symbol, qty in positions.items():
            assert isinstance(symbol, str)
            assert isinstance(qty, int)
            assert qty >= 0

        # 注意：目前是模拟实现，返回空字典
        # 如果未来实现真实连接，这里会测试真实持仓数据
