#!/bin/bash
# Regenerate Frontend Cache
# Run this script after updating trading data to regenerate the pre-computed cache files

set -e  # Exit on error

echo "========================================"
echo "Regenerating Frontend Cache"
echo "========================================"
echo ""

# 检测操作系统并设置 Python 命令
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
    # Windows 环境 (Git Bash/Cygwin)
    PYTHON_CMD="python"
else
    # Linux/Unix 环境
    PYTHON_CMD="python3"
fi

# Get script directory
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

# Check if PyYAML is installed
if ! $PYTHON_CMD -c "import yaml" &> /dev/null; then
    echo "Error: Python with PyYAML not found. Please install: pip install pyyaml"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
echo ""

# Run the cache generation script
echo "Running cache generation script..."
$PYTHON_CMD scripts/precompute_frontend_cache.py

echo ""
echo "========================================"
echo "Cache regeneration complete!"
echo "========================================"
echo ""
echo "Generated files:"
echo "  - docs/data/us_cache.json"
echo "  - docs/data/cn_cache.json"
echo ""
echo "These files will be automatically used by the frontend for faster loading."
echo "Commit these files to your repository for GitHub Pages deployment."
