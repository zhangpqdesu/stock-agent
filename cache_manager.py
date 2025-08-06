import os
import pandas as pd
from datetime import datetime

# 缓存目录
CACHE_PATH = os.path.join(os.path.dirname(__file__), "cache")

def ensure_cache_directory():
    """确保缓存目录存在"""
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)
        print(f"已创建缓存目录: {CACHE_PATH}")

def save_analysis_to_cache(ts_code, analysis_content, llm_provider, llm_model):
    """
    将分析报告保存到缓存文件
    
    Args:
        ts_code (str): 股票代码
        analysis_content (str): 分析报告内容
        llm_provider (str): 使用的LLM提供商
        llm_model (str): 使用的模型
    
    Returns:
        str: 缓存文件路径
    """
    ensure_cache_directory()
    
    # 生成文件名: {ts_code}_{YYYYMMDD}_{HHmmss}.csv
    current_time = datetime.now()
    date_str = current_time.strftime("%Y%m%d")
    time_str = current_time.strftime("%H%M%S")
    filename = f"{ts_code}_{date_str}_{time_str}.csv"
    filepath = os.path.join(CACHE_PATH, filename)
    
    # 创建包含分析报告和元数据的DataFrame
    cache_data = {
        'timestamp': [current_time.isoformat()],
        'ts_code': [ts_code],
        'llm_provider': [llm_provider],
        'llm_model': [llm_model],
        'analysis_content': [analysis_content],
        'file_date': [date_str],
        'file_time': [time_str]
    }
    
    df = pd.DataFrame(cache_data)
    
    try:
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"分析报告已缓存到: {filepath}")
        return filepath
    except Exception as e:
        print(f"保存缓存文件失败: {e}")
        return None

def get_cached_files(ts_code=None):
    """
    获取缓存文件列表
    
    Args:
        ts_code (str, optional): 如果指定，只返回该股票代码的缓存文件
    
    Returns:
        list: 缓存文件信息列表，每个元素是包含文件信息的字典
    """
    ensure_cache_directory()
    
    cached_files = []
    
    for filename in os.listdir(CACHE_PATH):
        if filename.endswith('.csv'):
            try:
                # 解析文件名
                # 文件名格式: {ts_code}_{YYYYMMDD}_{HHMMSS}.csv, e.g., 000001.SZ_20240728_153000.csv
                parts = filename.replace('.csv', '').split('_')
                if len(parts) == 3:
                    file_ts_code = parts[0]
                    file_date = parts[1]
                    file_time = parts[2]
                else:
                    # 如果文件名格式不匹配，则跳过
                    print(f"跳过格式不正确的缓存文件: {filename}")
                    continue
                    
                # 如果指定了ts_code，只返回匹配的文件
                if ts_code and file_ts_code != ts_code:
                    continue
                    
                filepath = os.path.join(CACHE_PATH, filename)
                
                # 安全地获取文件状态信息，避免名称空间冲突
                try:
                    # 使用 getattr 避免可能的名称冲突
                    stat_func = getattr(os, 'stat', None)
                    if stat_func and callable(stat_func):
                        file_stat = stat_func(filepath)
                        file_size = file_stat.st_size
                        modified_time = datetime.fromtimestamp(file_stat.st_mtime)
                    else:
                        # 如果 os.stat 不可用，使用 os.path.getsize 和 os.path.getmtime 作为替代
                        file_size = os.path.getsize(filepath)
                        modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                except Exception as stat_error:
                    print(f"获取文件状态失败 {filename}: {stat_error}")
                    # 使用默认值
                    file_size = 0
                    modified_time = datetime.now()
                
                # 尝试读取文件获取更多信息
                try:
                    df = pd.read_csv(filepath, encoding='utf-8-sig')
                    llm_info = f"{df.iloc[0]['llm_provider']} ({df.iloc[0]['llm_model']})" if 'llm_provider' in df.columns else "未知"
                except:
                    llm_info = "未知"
                
                cached_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'ts_code': file_ts_code,
                    'date': file_date,
                    'time': file_time,
                    'llm_info': llm_info,
                    'file_size': file_size,
                    'modified_time': modified_time,
                    'display_name': f"{file_ts_code} - {file_date} {file_time[:2]}:{file_time[2:4]} ({llm_info})"
                })
            except Exception as e:
                print(f"解析缓存文件 {filename} 失败: {e}")
                continue
    
    # 按修改时间倒序排列（最新的在前面）
    cached_files.sort(key=lambda x: x['modified_time'], reverse=True)
    
    return cached_files

def load_cached_analysis(filepath):
    """
    从缓存文件加载分析报告
    
    Args:
        filepath (str): 缓存文件路径
    
    Returns:
        tuple: (分析内容, 元数据字典) 或 (None, error_message)
    """
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        
        if df.empty or 'analysis_content' not in df.columns:
            return None, "缓存文件格式错误"
        
        analysis_content = df.iloc[0]['analysis_content']
        
        metadata = {
            'ts_code': df.iloc[0].get('ts_code', ''),
            'timestamp': df.iloc[0].get('timestamp', ''),
            'llm_provider': df.iloc[0].get('llm_provider', ''),
            'llm_model': df.iloc[0].get('llm_model', ''),
            'file_date': df.iloc[0].get('file_date', ''),
            'file_time': df.iloc[0].get('file_time', '')
        }
        
        return analysis_content, metadata
        
    except Exception as e:
        return None, f"加载缓存文件失败: {e}"