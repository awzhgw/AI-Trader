#!/bin/bash

# AI-Trader 主启动脚本
# 用于启动完整的交易环境
# 兼容 Windows (Git Bash/WSL) 和 Linux

set -e  # 遇到错误时退出

# 检测操作系统并设置 Python 命令
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
    # Windows 环境 (Git Bash/Cygwin)
    PYTHON_CMD="python"
    PYTHON3_CMD="python"
else
    # Linux/Unix 环境
    PYTHON_CMD="python"
    PYTHON3_CMD="python3"
fi

echo "🚀 Launching AI Trader Environment..."

# Get the project root directory (parent of scripts/)
# Windows 兼容的路径获取方式
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
    # Windows 环境：处理可能的反斜杠路径，转换为正斜杠
    SCRIPT_PATH="${BASH_SOURCE[0]}"
    SCRIPT_PATH="${SCRIPT_PATH//\\//}"  # 将反斜杠转换为正斜杠
    SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd -W 2>/dev/null || pwd )"
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd -W 2>/dev/null || pwd )"
    # 确保路径使用正斜杠
    SCRIPT_DIR="${SCRIPT_DIR//\\//}"
    PROJECT_ROOT="${PROJECT_ROOT//\\//}"
else
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
fi

cd "$PROJECT_ROOT"

echo "📊 Now getting and merging price data..."
cd data
$PYTHON_CMD get_daily_price.py
$PYTHON_CMD merge_jsonl.py
cd ..

echo "🔧 Now starting MCP services..."
cd agent_tools
$PYTHON_CMD start_mcp_services.py
cd ..

#waiting for MCP services to start
sleep 2

echo "🤖 Now starting the main trading agent..."
$PYTHON_CMD main.py configs/default_config.json

echo "✅ AI-Trader stopped"

echo "🔄 Starting web server..."
cd docs
$PYTHON3_CMD -m http.server 8888

echo "✅ Web server started"