"""
GjzjAdapter真实连接测试
使用真实的国金证券连接进行测试，但跳过买卖操作以避免真实交易
"""
import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
env_path = Path(__file__).resolve().parents[3] / '.env'
load_dotenv(env_path)

from brokers.gjzj.gjzj_adapter import GjzjAdapter
from brokers.broker_factory import BrokerAdapterFactory


class TestGjzjAdapterReal:
    """GjzjAdapter真实连接测试类"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self, request):
        """类级别的setup和teardown，只连接一次"""
        # 从 .env 读取配置
        cls = request.cls
        cls.account_id = os.getenv("GJZJ_ACCOUNT_ID", "default")
        cls.session_id = int(os.getenv("GJZJ_SESSION_ID", "0"))
        cls.gjzj_path = os.getenv("GJZJ_PATH")

        if not cls.gjzj_path:
            pytest.skip("GJZJ_PATH 未配置，跳过真实连接测试")

        # 创建适配器
        adapter = GjzjAdapter.create_from_config()

        # 清理测试文件
        project_root = Path(__file__).resolve().parent.parent.parent
        position_dir = project_root / "data" / "ai_positions"
        ai_position_file = position_dir / "gjzj_ai_positions.jsonl"
        if ai_position_file.exists():
            ai_position_file.unlink()

        # 连接一次（在第一个测试前）
        import platform
        if platform.system() == 'Windows':
            # 只在Windows环境下尝试连接
            if adapter.connect():
                cls.connection_failed = False
            else:
                print(f"\n⚠️ 警告: 连接国金证券失败 (Path: {cls.gjzj_path})")
                cls.connection_failed = True
        else:
            cls.connection_failed = True

        # 将适配器设置到类上，供所有测试方法使用
        cls.adapter = adapter

        yield

        # 清理
        if ai_position_file.exists():
            ai_position_file.unlink()

    def test_init(self):
        """测试初始化"""
        adapter = self.__class__.adapter
        assert adapter.broker_type == "gjzj"
        assert adapter.account_id == self.__class__.account_id
        assert adapter.session_id == self.__class__.session_id
        assert adapter.path == self.__class__.gjzj_path

    def test_connect(self):
        """测试真实连接（连接已在setup中完成，这里只验证连接状态）"""
        if self.__class__.connection_failed:
             pytest.skip("无法连接到国金证券，请检查配置和客户端状态")

    def test_get_price(self):
        """测试获取价格（使用本地数据）"""
        if self.__class__.connection_failed:
             pytest.skip("无法连接到国金证券，请检查配置和客户端状态")
        adapter = self.__class__.adapter
        # 如果未连接，跳过测试
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        # 测试获取A股价格（使用本地数据）
        try:
            price = adapter.get_price("600519.SH")
            assert isinstance(price, (int, float))
            assert price > 0
        except ValueError as e:
            # 如果数据不存在，跳过测试
            pytest.skip(f"无法获取价格数据: {e}")

    def test_buy_validation(self):
        """测试买入验证（不实际买入）"""
        if self.__class__.connection_failed:
             pytest.skip("无法连接到国金证券，请检查配置和客户端状态")
        adapter = self.__class__.adapter
        # 如果未连接，跳过测试
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        # 测试A股必须100的倍数
        result = adapter.buy("600519.SH", 50)  # 不是100的倍数
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
        if self.__class__.connection_failed:
             pytest.skip("无法连接到国金证券，请检查配置和客户端状态")
        adapter = self.__class__.adapter
        # 如果未连接，跳过测试
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        # 测试A股必须100的倍数
        result = adapter.sell("600519.SH", 50)  # 不是100的倍数
        assert result["success"] is False
        assert "multiples of 100" in result["error"].lower() or "100的倍数" in result["error"]

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_sell_protect_manual_position(self):
        """测试卖出保护人工持仓（不实际卖出）"""
        if self.__class__.connection_failed:
             pytest.skip("无法连接到国金证券，请检查配置和客户端状态")
        adapter = self.__class__.adapter
        # 如果未连接，跳过测试
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        # 获取当前持仓
        position = adapter.get_position("600519.SH")
        ai_position = position["ai_position"]

        # 尝试卖出超过AI持仓的数量
        if ai_position > 0:
            result = adapter.sell("600519.SH", ai_position + 100)
            assert result["success"] is False
            assert "AI持仓不足" in result["error"] or "持仓不足" in result["error"]
        else:
            pytest.skip("当前没有AI持仓，跳过测试")

    def test_fetch_account_info(self):
        """测试获取账户信息并打印账户余额"""
        if self.__class__.connection_failed:
             pytest.skip("无法连接到国金证券，请检查配置和客户端状态")
        adapter = self.__class__.adapter
        # 如果未连接，跳过测试
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        account_info = adapter._fetch_account_info()

        assert isinstance(account_info, dict)
        assert "cash" in account_info
        assert "total_asset" in account_info
        assert isinstance(account_info["cash"], (int, float))
        assert isinstance(account_info["total_asset"], (int, float))

    def test_fetch_total_positions(self):
        """测试获取总持仓"""
        if self.__class__.connection_failed:
             pytest.skip("无法连接到国金证券，请检查配置和客户端状态")
        adapter = self.__class__.adapter
        # 如果未连接，跳过测试
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        positions = adapter._fetch_total_positions()

        assert isinstance(positions, dict)
        # 验证持仓数据格式
        for symbol, qty in positions.items():
            assert isinstance(symbol, str)
            assert isinstance(qty, int)
            assert qty >= 0
        test_symbol = "600519.SH"
        position = adapter.get_position(test_symbol)

        assert isinstance(position, dict)
        assert position["symbol"] == test_symbol
        assert "total_position" in position
        assert "ai_position" in position
        assert "manual_position" in position

        assert isinstance(position["total_position"], int)
        assert isinstance(position["ai_position"], int)
        assert isinstance(position["manual_position"], int)
