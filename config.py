# ===== LLM API Keys =====
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 阿里通义千问 API 密钥
# 获取地址: https://dashscope.console.aliyun.com/
DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY', "your_dashscope_api_key_here")

# 🔍 Google AI API 密钥 (可选，用于Gemini模型)
# 获取地址: https://ai.google.dev/
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', "your_google_api_key_here")

# 🌍 OpenAI API 密钥 (可选，需要国外网络)
# 获取地址: https://platform.openai.com/
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', "your_openai_api_key_here")

# 🌐 OpenRouter API 密钥 (可选，聚合多个AI模型)
# 获取地址: https://openrouter.ai/
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', "your_openrouter_api_key_here")

# 🤖 Anthropic API 密钥 (可选，用于Claude模型)
# 获取地址: https://console.anthropic.com/
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', "your_anthropic_api_key_here")

# 🚀 DeepSeek V3 API 密钥 (推荐，性价比极高的国产大模型)
# 获取地址: https://platform.deepseek.com/
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', "your_deepseek_api_key_here")
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', "https://api.deepseek.com")
DEEPSEEK_ENABLED = os.environ.get('DEEPSEEK_ENABLED', "false").lower() == "true"


# ===== Data Source API Keys =====

# 📊 FinnHub API 密钥 (必需，用于获取美股金融数据)
# 获取地址: https://finnhub.io/
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', "your_finnhub_api_key_here")

# 📈 Tushare API Token (推荐，专业的中国金融数据源)
# 获取地址: https://tushare.pro/register?reg=128886
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', "your_tushare_token_here")
TUSHARE_ENABLED = os.environ.get('TUSHARE_ENABLED', "true").lower() == "true"

# 🎯 默认中国股票数据源 (推荐设置为akshare)
# 可选值: akshare, tushare, baostock, tdx(已弃用)
DEFAULT_CHINA_DATA_SOURCE = os.environ.get('DEFAULT_CHINA_DATA_SOURCE', "akshare")

# 本地数据存储路径
DATA_PATH = os.path.abspath(f'D:\股票研究\机器学习模型\data')
