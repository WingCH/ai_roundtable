"""
配置和環境變數
"""

import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 載入環境變數
load_dotenv()

# 獲取環境變數
API_KEY = os.getenv("OPENROUTER_API_KEY")
TIMEOUT = int(os.getenv("TIMEOUT", "900"))  # 默認900秒
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))  # 默認0.7

if not API_KEY:
    print("警告: 未設置 OPENROUTER_API_KEY 環境變數")

# 初始化 OpenAI 客戶端（使用異步版本）
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
    timeout=TIMEOUT
)

# 可用的模型列表
AVAILABLE_MODELS = [
    # "deepseek/deepseek-r1",
    # "openai/chatgpt-4o-latest",
    # "anthropic/claude-3.7-sonnet",
    "deepseek/deepseek-chat-v3-0324"
]

# 模型輪詢計數器
model_counter = 0 