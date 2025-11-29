#!/bin/bash

# 兼容 Windows (Git Bash/WSL) 和 Linux

# 检测操作系统并设置 Python 命令
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
    # Windows 环境 (Git Bash/Cygwin)
    PYTHON_CMD="python"
else
    # Linux/Unix 环境
    PYTHON_CMD="python"
fi

# 获取项目根目录（scripts/ 的父目录）
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

echo "🤖 正在启动主交易智能体（A股模式）..."

$PYTHON_CMD main.py configs/astock_hour_config.json  # 运行A股配置


echo "✅ AI-Trader 已停止"
