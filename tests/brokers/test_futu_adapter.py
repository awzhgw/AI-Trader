"""
FutuAdapter真实连接测试
使用真实的富途证券连接进行测试，但跳过买卖操作以避免真实交易
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

from brokers.futu.futu_adapter import FutuAdapter
from brokers.broker_factory import BrokerAdapterFactory


class TestFutuAdapterReal:
    """FutuAdapter真实连接测试类"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_and_teardown(self, request):
        """类级别的setup和teardown，只连接一次"""
        cls = request.cls
        cls.account_id = os.getenv("FUTU_ACCOUNT_ID", "default")
        cls.host = os.getenv("FUTU_HOST", "127.0.0.1")
        cls.port = int(os.getenv("FUTU_PORT", "11111"))
        cls.market = os.getenv("FUTU_MARKET", "US")
        cls.security_firm = os.getenv("FUTU_SECURITY_FIRM", "")

        # 根据市场类型选择测试股票代码
        cls.test_symbol = "AAPL" if cls.market.upper() == "US" else "00700"  # 美股用AAPL，港股用00700（腾讯）

        adapter = FutuAdapter.create_from_config()
        project_root = Path(__file__).resolve().parent.parent.parent
        ai_position_file = project_root / "data" / "ai_positions" / "futu_ai_positions.jsonl"

        # 清理测试文件
        if ai_position_file.exists():
            ai_position_file.unlink()

        # 连接
        adapter.connect()
        cls.adapter = adapter

        yield

        # 清理
        if ai_position_file.exists():
            ai_position_file.unlink()
        for ctx in [adapter._quote_ctx, adapter._trade_ctx]:
            if ctx:
                try:
                    ctx.close()
                except:
                    pass

    def test_init(self):
        """测试初始化"""
        adapter = self.__class__.adapter
        assert adapter.broker_type == "futu"
        assert adapter.account_id == self.__class__.account_id
        assert adapter.host == self.__class__.host
        assert adapter.port == self.__class__.port
        assert adapter.market == self.__class__.market
        assert adapter.security_firm == self.__class__.security_firm

    def test_connect(self):
        """测试真实连接（连接已在setup中完成，这里只验证连接状态并打印账户信息）"""
        adapter = self.__class__.adapter
        # 连接已在setup中完成，这里只验证连接状态
        # 如果连接失败，跳过测试
        if not adapter._connected:
            pytest.skip("无法连接到富途证券，请检查配置和网络连接")

        assert adapter._connected is True
        # 检查连接状态
        if hasattr(adapter, '_quote_ctx') and adapter._quote_ctx:
            assert adapter._quote_ctx is not None

        # 连接成功后，打印账户余额和持仓信息
        currency_symbol = "$" if adapter.market.upper() == "US" else "HK$"
        print("\n" + "=" * 60)
        print("🔗 富途证券连接成功")
        print("=" * 60)
        print(f"账户ID: {adapter.account_id}")
        print(f"市场: {adapter.market}")
        print(f"主机: {adapter.host}:{adapter.port}")
        print(f"交易上下文: {'已创建' if adapter._trade_ctx else '未创建'}")
        print("=" * 60)

        # 如果交易上下文已创建，获取并打印账户余额和持仓
        if adapter._trade_ctx:
            try:
                # 获取账户信息
                account_info = adapter._fetch_account_info()
                print("\n💰 账户余额信息")
                print("-" * 60)
                print(f"现金余额: {currency_symbol}{account_info['cash']:,.2f}")
                print(f"总资产: {currency_symbol}{account_info['total_asset']:,.2f}")
                print("-" * 60)

                # 获取持仓信息
                positions = adapter._fetch_total_positions()
                print("\n📊 持仓信息")
                print("-" * 60)
                if positions:
                    print(f"持仓数量: {len(positions)} 只股票")
                    print("\n持仓明细:")
                    for symbol, qty in sorted(positions.items()):
                        print(f"  {symbol:10s} | {qty:6d} 股")
                else:
                    print("当前无持仓")
                print("-" * 60)
            except RuntimeError as e:
                print(f"\n⚠️ 警告: 获取账户信息失败: {e}")
                print("提示: 请检查FutuOpenD是否已登录并启用交易权限")
            except Exception as e:
                print(f"\n⚠️ 警告: 获取账户信息失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\nℹ️  提示: 交易上下文未创建，无法获取账户余额和持仓信息")
            print("=" * 60)
            print("可能的原因：")
            print("  1. FutuOpenD未登录或未启用交易权限")
            print("  2. 市场类型配置错误（当前市场: {})".format(adapter.market))
            print("  3. 连接测试失败（请查看上方的警告信息）")
            print("=" * 60)

        print("\n" + "=" * 60 + "\n")

    def test_get_price(self):
        """测试获取价格"""
        adapter = self.__class__.adapter
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        test_symbol = self.__class__.test_symbol
        try:
            price = adapter.get_price(test_symbol)
            assert isinstance(price, (int, float)) and price > 0
        except ValueError as e:
            pytest.skip(f"无法获取价格数据: {e}")

    def test_get_position(self):
        """测试获取持仓信息并打印持仓情况"""
        adapter = self.__class__.adapter
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        if not adapter._trade_ctx:
            print("\n" + "=" * 60)
            print("ℹ️  提示: 交易上下文未创建，无法获取真实持仓和账户信息")
            print("请确保FutuOpenD已登录并启用交易权限")
            print("=" * 60 + "\n")

        position = adapter.get_position()

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

        # 打印持仓信息
        currency_symbol = "$" if adapter.market.upper() == "US" else "HK$"
        print("\n" + "=" * 60)
        print("📊 富途证券持仓情况")
        print("=" * 60)
        print(f"账户ID: {adapter.account_id}")
        print(f"现金余额: {currency_symbol}{position['cash']:,.2f}")
        print(f"总资产: {currency_symbol}{position['total_asset']:,.2f}")
        print("-" * 60)

        total_positions = position["total_positions"]
        ai_positions = position["ai_positions"]
        manual_positions = position["manual_positions"]

        if total_positions:
            print("\n总持仓:")
            for symbol, qty in sorted(total_positions.items()):
                ai_qty = ai_positions.get(symbol, 0)
                manual_qty = manual_positions.get(symbol, 0)
                print(f"  {symbol:10s} | 总持仓: {qty:6d} | AI持仓: {ai_qty:6d} | 人工持仓: {manual_qty:6d}")
        else:
            print("\n当前无持仓")

        if ai_positions:
            print("\nAI持仓:")
            for symbol, qty in sorted(ai_positions.items()):
                print(f"  {symbol:10s} | {qty:6d} 股")
        else:
            print("\n当前无AI持仓")

        if manual_positions:
            print("\n人工持仓:")
            for symbol, qty in sorted(manual_positions.items()):
                print(f"  {symbol:10s} | {qty:6d} 股")
        else:
            print("\n当前无人工持仓")

        print("=" * 60 + "\n")

    def test_get_position_by_symbol(self):
        """测试获取指定股票的持仓"""
        adapter = self.__class__.adapter
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        test_symbol = self.__class__.test_symbol
        position = adapter.get_position(test_symbol)
        assert isinstance(position, dict) and position["symbol"] == test_symbol
        assert all(key in position for key in ["total_position", "ai_position", "manual_position"])
        assert all(isinstance(position[key], int) for key in ["total_position", "ai_position", "manual_position"])

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_buy_validation(self):
        """测试买入验证（不实际买入）"""
        adapter = self.__class__.adapter
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        test_symbol = self.__class__.test_symbol
        result = adapter.buy(test_symbol, 10)
        assert isinstance(result, dict) and "success" in result

    @pytest.mark.skipif(
        os.getenv("SKIP_TRADE_TESTS", "true").lower() == "true",
        reason="跳过买卖操作测试以避免真实交易"
    )
    def test_sell_protect_manual_position(self):
        """测试卖出保护人工持仓（不实际卖出）"""
        adapter = self.__class__.adapter
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        test_symbol = self.__class__.test_symbol
        ai_position = adapter.get_position(test_symbol)["ai_position"]
        if ai_position == 0:
            pytest.skip("当前没有AI持仓，跳过测试")

        result = adapter.sell(test_symbol, ai_position + 10)
        assert not result["success"] and ("AI持仓不足" in result["error"] or "持仓不足" in result["error"])

    def test_fetch_account_info(self):
        """测试获取账户信息并打印账户余额"""
        adapter = self.__class__.adapter
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        if not adapter._trade_ctx:
            pytest.skip("交易上下文未创建，跳过测试")

        try:
            account_info = adapter._fetch_account_info()
            assert isinstance(account_info, dict) and "cash" in account_info and "total_asset" in account_info
            assert isinstance(account_info["cash"], (int, float)) and isinstance(account_info["total_asset"], (int, float))

        except RuntimeError as e:
            pytest.skip(f"无法获取账户信息: {e}")

    def test_fetch_total_positions(self):
        """测试获取总持仓"""
        adapter = self.__class__.adapter
        if not adapter._connected:
            pytest.skip("无法连接，跳过测试")

        positions = adapter._fetch_total_positions()
        assert isinstance(positions, dict)
        for symbol, qty in positions.items():
            assert isinstance(symbol, str) and isinstance(qty, int) and qty >= 0
