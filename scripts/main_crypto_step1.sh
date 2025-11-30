#!/bin/bash

# A股数据准备

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
 
# 确保 data/crypto 存在并进入该目录
mkdir -p "$PROJECT_ROOT/data/crypto"
cd "$PROJECT_ROOT/data/crypto" || { echo "无法进入目录 $PROJECT_ROOT/data/crypto"; exit 1; }
 
# 在运行 python 前输出当前工作目录
echo "当前运行目录: $(pwd)"
echo "即将运行: $PYTHON_CMD get_daily_price_crypto.py"
$PYTHON_CMD get_daily_price_crypto.py
 
echo "当前运行目录: $(pwd)"
echo "即将运行: $PYTHON_CMD merge_crypto_jsonl.py"
$PYTHON_CMD merge_crypto_jsonl.py
 
# # for tushare
# echo "当前运行目录: $(pwd)"
# echo "即将运行: $PYTHON_CMD get_daily_price_tushare.py"
# $PYTHON_CMD get_daily_price_tushare.py
# echo "当前运行目录: $(pwd)"
# echo "即将运行: $PYTHON_CMD merge_jsonl_tushare.py"
# $PYTHON_CMD merge_jsonl_tushare.py

cd ..
