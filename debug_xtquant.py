import os
import sys

try:
    from xtquant import xttrader
except ImportError:
    print("❌ 无法导入 xtquant 模块。请确保已安装该模块。")
    sys.exit(1)

# 从 .env 或直接硬编码路径
# 这里我们使用用户之前配置的路径
path = r"D:\deepstock\gjzqqmt\userdata_mini"
session_id = 123456

print("="*50)
print("XtQuant 连接诊断工具")
print("="*50)

print(f"检查路径: {path}")
if os.path.exists(path):
    print("✅ 路径存在")
else:
    print("❌ 路径不存在！请检查路径配置。")
    # 尝试探测可能的路径
    parent = os.path.dirname(path)
    if os.path.exists(parent):
        print(f"   父目录 {parent} 存在。该目录下的内容:")
        try:
            print(f"   {os.listdir(parent)}")
        except:
            pass
    sys.exit(1)

print(f"尝试连接 Session ID: {session_id} ...")
print("请确保 MiniQMT 客户端已启动并登录！")

try:
    print(f"尝试连接 Session ID: {session_id} ...")
    trader = xttrader.XtQuantTrader(path, session_id)
    trader.start()
    result = trader.connect()
    
    if result == 0:
        print(f"✅ 连接成功！(返回码: {result})")
except Exception as e:
    print(f"❌ 发生异常: {e}")

print("="*50)
