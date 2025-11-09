"""
GjzjAdapter真实连接测试
使用真实的国金证券连接进行测试，但跳过买卖操作以避免真实交易
"""
import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)

from brokers.gjzj.gjzj_adapter import GjzjAdapter
from brokers.broker_factory import BrokerAdapterFactory


class TestGjzjAdapterReal:
    """GjzjAdapter真实连接测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试方法前后执行"""
        # 从 .env 读取配置
        self.account_id = os.getenv("GJZJ_ACCOUNT_ID", "default")
        self.session_id = int(os.getenv("GJZJ_SESSION_ID", "0"))
        self.gjzj_path = os.getenv("GJZJ_PATH")

        if not self.gjzj_path:
            pytest.skip("GJZJ_PATH 未配置，跳过真实连接测试")

        # 创建适配器
        self.adapter = GjzjAdapter.create_from_config()

        # 清理测试文件
        self._cleanup_test_files()

        yield

        # 测试后清理
        self._cleanup_test_files()
        # 断开连接
        if hasattr(self.adapter, '_connected') and self.adapter._connected:
            try:
                if self.adapter.trader:
                    self.adapter.trader.stop()
            except:
                pass

    def _cleanup_test_files(self):
        """清理测试文件"""
        project_root = Path(__file__).resolve().parent.parent.parent
        position_dir = project_root / "data" / "ai_positions"
        ai_position_file = position_dir / "gjzj_ai_positions.jsonl"
        if ai_position_file.exists():
            ai_position_file.unlink()

    def test_init(self):
        """测试初始化"""
        assert self.adapter.broker_type == "gjzj"
        assert self.adapter.account_id == self.account_id
        assert self.adapter.session_id == self.session_id
        assert self.adapter.path == self.gjzj_path

    def test_connect(self):
        """测试真实连接"""
        import platform

        # 检查运行环境
        if platform.system() != 'Windows':
            pytest.skip(
                f"XtQuant库主要支持Windows系统，当前系统: {platform.system()}\n"
                "在Linux/WSL环境中，xtpythonclient模块无法加载，无法进行真实连接测试。\n"
                "建议在Windows环境中运行此测试，或使用模拟交易模式。"
            )

        result = self.adapter.connect()

        # 连接可能成功或失败，取决于实际环境
        # 如果连接失败，打印错误信息但不失败测试
        if not result:
            pytest.skip(f"无法连接到国金证券，请检查配置和网络连接")

        assert result is True
        assert self.adapter._connected is True
        assert self.adapter.trader is not None

    def test_get_price(self):
        """测试获取价格（使用本地数据）"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

        # 测试获取A股价格（使用本地数据）
        try:
            price = self.adapter.get_price("600519.SH")
            assert isinstance(price, (int, float))
            assert price > 0
        except ValueError as e:
            # 如果数据不存在，跳过测试
            pytest.skip(f"无法获取价格数据: {e}")

    def test_get_position(self):
        """测试获取持仓信息并打印账户余额"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

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

        # 打印账户余额和持仓信息
        print("\n" + "=" * 60)
        print("📊 国金证券账户余额和持仓信息")
        print("=" * 60)
        print(f"账户ID: {self.adapter.account_id}")
        print(f"现金余额: ¥{position['cash']:,.2f}")
        print(f"总资产: ¥{position['total_asset']:,.2f}")
        print(f"\n总持仓数量: {len(position['total_positions'])} 只股票")
        print(f"AI持仓数量: {len(position['ai_positions'])} 只股票")
        print(f"人工持仓数量: {len(position['manual_positions'])} 只股票")

        if position['total_positions']:
            print("\n持仓明细:")
            for symbol, qty in position['total_positions'].items():
                ai_qty = position['ai_positions'].get(symbol, 0)
                manual_qty = position['manual_positions'].get(symbol, 0)
                print(f"  {symbol}: 总持仓={qty}股, AI持仓={ai_qty}股, 人工持仓={manual_qty}股")

        print("=" * 60 + "\n")

    def test_get_position_by_symbol(self):
        """测试获取指定股票的持仓"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

        # 测试获取指定股票持仓
        test_symbol = "600519.SH"
        position = self.adapter.get_position(test_symbol)

        assert isinstance(position, dict)
        assert position["symbol"] == test_symbol
        assert "total_position" in position
        assert "ai_position" in position
        assert "manual_position" in position

        assert isinstance(position["total_position"], int)
        assert isinstance(position["ai_position"], int)
        assert isinstance(position["manual_position"], int)

    def test_buy_validation(self):
        """测试买入验证（不实际买入）"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

        # 测试A股必须100的倍数
        result = self.adapter.buy("600519.SH", 50)  # 不是100的倍数
        assert result["success"] is False
        assert "multiples of 100" in result["error"].lower() or "100的倍数" in result["error"]

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_buy_not_connected(self):
        """测试买入失败（未连接）"""
        # 创建一个未连接的适配器
        adapter = GjzjAdapter.create_from_config()
        adapter._connected = False
        adapter.trader = None

        result = adapter.buy("600519.SH", 100)
        assert result["success"] is False
        assert "未连接" in result["error"]

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_sell_validation(self):
        """测试卖出验证（不实际卖出）"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

        # 测试A股必须100的倍数
        result = self.adapter.sell("600519.SH", 50)  # 不是100的倍数
        assert result["success"] is False
        assert "multiples of 100" in result["error"].lower() or "100的倍数" in result["error"]

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_sell_protect_manual_position(self):
        """测试卖出保护人工持仓（不实际卖出）"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

        # 获取当前持仓
        position = self.adapter.get_position("600519.SH")
        ai_position = position["ai_position"]

        # 尝试卖出超过AI持仓的数量
        if ai_position > 0:
            result = self.adapter.sell("600519.SH", ai_position + 100)
            assert result["success"] is False
            assert "AI持仓不足" in result["error"] or "持仓不足" in result["error"]
        else:
            pytest.skip("当前没有AI持仓，跳过测试")

    def test_fetch_account_info(self):
        """测试获取账户信息并打印账户余额"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

        account_info = self.adapter._fetch_account_info()

        assert isinstance(account_info, dict)
        assert "cash" in account_info
        assert "total_asset" in account_info
        assert isinstance(account_info["cash"], (int, float))
        assert isinstance(account_info["total_asset"], (int, float))

        # 打印账户余额信息
        print("\n" + "=" * 60)
        print("📊 国金证券账户信息")
        print("=" * 60)
        print(f"账户ID: {self.adapter.account_id}")
        print(f"现金余额: ¥{account_info['cash']:,.2f}")
        print(f"总资产: ¥{account_info['total_asset']:,.2f}")
        print("=" * 60 + "\n")

    def test_fetch_total_positions(self):
        """测试获取总持仓"""
        # 确保已连接
        if not self.adapter._connected:
            self.adapter.connect()
            if not self.adapter._connected:
                pytest.skip("无法连接，跳过测试")

        positions = self.adapter._fetch_total_positions()

        assert isinstance(positions, dict)
        # 验证持仓数据格式
        for symbol, qty in positions.items():
            assert isinstance(symbol, str)
            assert isinstance(qty, int)
            assert qty >= 0
