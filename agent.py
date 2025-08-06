import json
import config
from data_handler import load_stock_data
from prompts import get_analysis_prompt
from llm_services import call_llm
from cache_manager import save_analysis_to_cache

class StockAnalystAgent:
    """
    股票分析师Agent - 核心协调器
    
    职责：
    1. 协调各个模块完成股票分析任务
    2. 串联数据获取、LLM分析和缓存保存流程
    """
    
    def __init__(self):
        print(f"股票分析师Agent已初始化")

    def analyze_stock(self, ts_code, llm_provider, llm_model):
        """
        执行股票分析的核心方法
        
        Args:
            ts_code (str): 股票代码
            llm_provider (str): LLM提供商
            llm_model (str): LLM模型
            
        Returns:
            str: 分析报告内容
        """
        # 1. 加载数据
        stock_data, error = load_stock_data(ts_code)
        if error:
            return f"**分析错误**: {error}"

        # 2. 将所有数据合并到一个JSON字符串中
        full_data_json = json.dumps(stock_data, ensure_ascii=False, indent=2)

        # 3. 生成Prompt
        prompt = get_analysis_prompt(ts_code, full_data_json)

        # 4. 调用LLM进行分析
        print(f"正在使用 {llm_provider} 的 {llm_model} 为 {ts_code} 生成分析报告...")
        
        analysis_result = call_llm(llm_provider, llm_model, prompt)

        # 5. 保存分析结果到缓存
        cache_path = save_analysis_to_cache(ts_code, analysis_result, llm_provider, llm_model)
        if cache_path:
            print(f"分析报告已缓存: {cache_path}")

        return analysis_result