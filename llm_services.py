import config
import google.generativeai as genai
import dashscope
from openai import OpenAI
import streamlit as st
import re

# --- LLM Provider and Model Configuration ---
LLM_PROVIDERS = {
    "Gemini": {
        "api_key": config.GOOGLE_API_KEY,
        "models": ["gemini-2.5-pro", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest"],
        "default_model": "gemini-2.5-pro"
    },
    "DashScope (Qwen)": {
        "api_key": config.DASHSCOPE_API_KEY,
        "models": ["qwen-turbo", "qwen-plus-latest", "qwen-max", "qwen-max-longcontext","qwen-plus"],
        "default_model": "qwen-plus-latest"
    },
    "DeepSeek": {
        "api_key": config.DEEPSEEK_API_KEY,
        "base_url": config.DEEPSEEK_BASE_URL,
        "models": ["deepseek-chat", "deepseek-coder"],
        "default_model": "deepseek-chat"
    },
    "OpenAI": {
        "api_key": config.OPENAI_API_KEY,
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "default_model": "gpt-4o"
    },
    "OpenRouter": {
        "api_key": config.OPENROUTER_API_KEY,
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "google/gemini-flash-1.5", "anthropic/claude-3-haiku", 
            "mistralai/mistral-7b-instruct", "meta-llama/llama-3-8b-instruct"
        ],
        "default_model": "google/gemini-flash-1.5"
    }
}

def get_llm_client(provider, model_name):
    """根据提供商和模型名称获取LLM客户端和配置"""
    provider_info = LLM_PROVIDERS.get(provider)
    if not provider_info:
        raise ValueError(f"未知的LLM提供商: {provider}")

    api_key = provider_info.get("api_key")
    if not api_key or "your_" in api_key:
        st.error(f"请在 `config.py` 文件中或环境变量中设置 {provider} 的 API Key。")
        return None, None

    if provider == "Gemini":
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(model_name)
        return client, "gemini"
    elif provider == "DashScope (Qwen)":
        dashscope.api_key = api_key
        return model_name, "dashscope"
    elif provider in ["OpenAI", "DeepSeek", "OpenRouter"]:
        client = OpenAI(
            api_key=api_key,
            base_url=provider_info.get("base_url")
        )
        return client, "openai_compatible"
    
    raise ValueError(f"不支持的LLM提供商: {provider}")

def call_llm(provider, model_name, prompt):
    """
    调用LLM进行分析
    
    Args:
        provider (str): LLM提供商
        model_name (str): 模型名称
        prompt (str): 分析提示词
    
    Returns:
        str: LLM生成的分析报告
    """
    try:
        client, client_type = get_llm_client(provider, model_name)
        if not client:
            return "**LLM客户端初始化失败**，请检查API密钥配置。"

        print(f"正在使用 {provider} 的 {model_name} 生成分析报告...")
        
        if client_type == "gemini":
            response = client.generate_content(prompt)
            cleaned_text = re.sub(r'^```markdown\s*|```$', '', response.text, flags=re.MULTILINE)
        elif client_type == "dashscope":
            response = dashscope.Generation.call(
                model=client,
                messages=[{'role': 'user', 'content': prompt}],
                result_format='message',  # 重要：指定返回格式为message
                temperature=0.1,
                top_p=0.9
            )
            if response.status_code == 200:
                cleaned_text = response.output.choices[0].message.content
            else:
                error_message = f"DashScope API Error: Code={response.code}, Message={response.message}"
                st.error(error_message)
                print(error_message)
                cleaned_text = f"**分析失败**: {error_message}"

        elif client_type == "openai_compatible":
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            cleaned_text = response.choices[0].message.content
        
        return cleaned_text
    except Exception as e:
        return f"**API调用失败**: {e}"