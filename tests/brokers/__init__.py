"""Tests for broker adapters"""
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件配置
# 从项目根目录加载 .env 文件
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)
