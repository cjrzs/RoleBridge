"""
RoleBridge 统一配置管理模块
集中管理所有环境变量配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 获取项目根目录（config.py 所在目录）
BASE_DIR = Path(__file__).parent

# 加载 .env 文件（从项目根目录）
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# CORS 配置
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

