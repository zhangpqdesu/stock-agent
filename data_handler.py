import pandas as pd
import numpy as np
import time
import json
import tushare as ts
import config
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

# --- Tushare Pro Initialization ---
pro = None
if config.TUSHARE_TOKEN and 'your_token' not in config.TUSHARE_TOKEN:
    ts.set_token(config.TUSHARE_TOKEN)
    pro = ts.pro_api()
    print("Tushare Pro接口在data_handler中初始化成功。")
else:
    print("警告: Tushare Token未在config.py中配置。部分数据获取功能将受限。")

# --- 带重试机制的数据获取 ---
def safe_get_data(func, max_retries=3, delay=1):
    """带重试机制的数据获取装饰器"""
    def wrapper(*args, **kwargs):
        for i in range(max_retries):
            try:
                # Tushare API限流，增加一个微小的延时
                time.sleep(0.1) 
                return func(*args, **kwargs)
            except Exception as e:
                print(f"请求失败: {e}, 剩余{max_retries-i-1}次重试机会")
                time.sleep(delay)
        return pd.DataFrame()
    return wrapper

# --- API 数据获取函数 ---

@safe_get_data
def get_basic_info(ts_code):
    """获取上市公司基本信息"""
    if not pro:
        print("Tushare Pro接口未初始化。")
        return pd.DataFrame()
    return pro.stock_company(ts_code=ts_code, fields='ts_code,exchange,chairman,manager,secretary,reg_capital,setup_date,province,city,introduction,website,email,office,employees,main_business,business_scope')

@safe_get_data
def get_quotes(ts_code, start_date, end_date):
    """获取股票行情数据"""
    if not pro: return pd.DataFrame()
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
    if df is not None and not df.empty:
        df['trade_date'] = df['trade_date'].astype(str)
        df = df.sort_values('trade_date', ascending=True)
    return df

@safe_get_data
def get_fundamentals(ts_code, start_date, end_date):
    """获取股票基本面数据"""
    if not pro: return pd.DataFrame()
    df = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is not None and not df.empty:
        df['trade_date'] = df['trade_date'].astype(str)
        df = df.sort_values('trade_date', ascending=True)
    return df

@safe_get_data
def get_moneyflow(ts_code, start_date, end_date):
    """获取股票资金流向数据"""
    if not pro: return pd.DataFrame()
    df = pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is not None and not df.empty:
        df['trade_date'] = df['trade_date'].astype(str)
        df = df.sort_values('trade_date', ascending=True)
    return df

@safe_get_data
def get_income(ts_code):
    """获取单只股票所有的历史利润表数据。"""
    if not pro: return pd.DataFrame()
    # 全量获取，不设置日期范围，以获取所有历史数据
    df = pro.income(ts_code=ts_code, fields='ts_code,ann_date,end_date,n_income_attr_p,total_revenue')
    if df is not None and not df.empty:
        df['ann_date'] = df['ann_date'].astype(str)
        df = df.sort_values('ann_date', ascending=True)
    return df

@safe_get_data
def get_weekly_data(ts_code):
    """获取最近5年的周线数据"""
    if not pro: return pd.DataFrame()
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y%m%d')
    df = pro.stk_week_month_adj(
        ts_code=ts_code,
        freq='week',
        start_date=start_date,
        end_date=end_date,
        fields='ts_code,trade_date,end_date,freq,open,high,low,close,pre_close,open_qfq,high_qfq,low_qfq,close_qfq,vol,amount,change,pct_chg'
    )
    if df is not None and not df.empty:
        df = df.sort_values('trade_date').reset_index(drop=True)
    return df

@safe_get_data
def get_factors_data(ts_code):
    """获取最近30天的专业因子数据"""
    if not pro: return pd.DataFrame()
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    df = pro.stk_factor_pro(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date
    )
    if df is not None and not df.empty:
        df = df.sort_values('trade_date').reset_index(drop=True)
    return df

# --- 指标计算函数 ---

def calculate_weekly_kdj(df_weekly):
    """计算周线KDJ指标，使用前复权数据"""
    if df_weekly.empty:
        return df_weekly
    
    df = df_weekly.copy()
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    low_n = df['low_qfq'].rolling(window=9, min_periods=1).min()
    high_n = df['high_qfq'].rolling(window=9, min_periods=1).max()
    
    rsv = np.where(
        (high_n - low_n) != 0,
        (df['close_qfq'] - low_n) / (high_n - low_n) * 100,
        0
    )
    
    df['k'] = pd.Series(rsv).ewm(com=2, adjust=False).mean()
    df['d'] = df['k'].ewm(com=2, adjust=False).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    golden_cross = (df['k'].shift(1) < df['d'].shift(1)) & (df['k'] > df['d'])
    dead_cross = (df['k'].shift(1) > df['d'].shift(1)) & (df['k'] < df['d'])
    df['kdj_cross'] = np.where(golden_cross, 'Golden Cross', np.where(dead_cross, 'Dead Cross', 'None'))
    
    return df

def analyze_professional_indicators(df_factors):
    """分析专业指标数据，提取关键信息。"""
    if df_factors.empty:
        return "专业指标数据缺失，无法进行分析。"

    latest_factors = df_factors.iloc[-1]
    analysis_parts = []
    
    if 'bbi_qfq' in latest_factors and pd.notna(latest_factors['bbi_qfq']):
        bbi = latest_factors['bbi_qfq']
        close = latest_factors['close_qfq']
        analysis_parts.append(f"BBI多空指标: {bbi:.2f}。当前股价 ({close:.2f}) {'高于' if close > bbi else '低于'}BBI，表明市场目前处于{'多头' if close > bbi else '空头'}行情。")

    if 'cci_qfq' in latest_factors and pd.notna(latest_factors['cci_qfq']):
        cci = latest_factors['cci_qfq']
        status = "常态"
        if cci > 100: status = "超买"
        elif cci < -100: status = "超卖"
        analysis_parts.append(f"CCI顺势指标: {cci:.2f}，目前处于{status}区域。")

    if 'dmi_pdi_qfq' in latest_factors and 'dmi_mdi_qfq' in latest_factors and 'dmi_adx_qfq' in latest_factors and pd.notna(latest_factors['dmi_pdi_qfq']):
        pdi, mdi, adx = latest_factors['dmi_pdi_qfq'], latest_factors['dmi_mdi_qfq'], latest_factors['dmi_adx_qfq']
        trend = "上升" if pdi > mdi else "下降"
        analysis_parts.append(f"DMI动向指标: PDI={pdi:.2f}, MDI={mdi:.2f}, ADX={adx:.2f}。目前为{trend}趋势，趋势强度为 {adx:.2f}。")

    if 'kdj_k_qfq' in latest_factors and 'kdj_d_qfq' in latest_factors and 'kdj_qfq' in latest_factors and pd.notna(latest_factors['kdj_k_qfq']):
        k, d, j = latest_factors['kdj_k_qfq'], latest_factors['kdj_d_qfq'], latest_factors['kdj_qfq']
        analysis_parts.append(f"KDJ随机指标: K={k:.2f}, D={d:.2f}, J={j:.2f}。")

    if 'macd_dif_qfq' in latest_factors and 'macd_dea_qfq' in latest_factors and 'macd_qfq' in latest_factors and pd.notna(latest_factors['macd_dif_qfq']):
        dif, dea, macd = latest_factors['macd_dif_qfq'], latest_factors['macd_dea_qfq'], latest_factors['macd_qfq']
        cross = "金叉" if dif > dea else "死叉"
        analysis_parts.append(f"MACD指标: DIF={dif:.2f}, DEA={dea:.2f}, MACD柱={macd:.2f}。当前处于{cross}状态。")

    if 'rsi_qfq_12' in latest_factors and pd.notna(latest_factors['rsi_qfq_12']):
        rsi = latest_factors['rsi_qfq_12']
        status = "常态"
        if rsi > 80: status = "超买"
        elif rsi < 20: status = "超卖"
        analysis_parts.append(f"RSI相对强弱指标(12日): {rsi:.2f}，目前处于{status}区域。")

    return " ".join(analysis_parts) if analysis_parts else "无可用专业指标进行分析。"

def calculate_technical_indicators(df_quotes, df_moneyflows=None, df_weekly=None, ts_code=None):
    """
    计算所有需要的技术指标，包括基础指标、周线KDJ和布林带突破。
    """
    if df_quotes.empty:
        return pd.DataFrame()

    df = df_quotes.copy()
    if df_moneyflows is not None and not df_moneyflows.empty:
        df = pd.merge(df, df_moneyflows[['trade_date', 'net_mf_amount']], on='trade_date', how='left')

    df = df.sort_values('trade_date').reset_index(drop=True)

    # --- 基础技术指标 ---
    for period in [20, 60, 120, 240]:
        df[f'returns_{period}d'] = df['close'].pct_change(period)

    for window in [5, 10, 20, 50, 200]:
        df[f'ma_{window}'] = df['close'].rolling(window=window, min_periods=int(window*0.8)).mean()

    df['volatility_20d'] = df['close'].pct_change().rolling(window=20, min_periods=10).std() * np.sqrt(20)
    df['volatility_60d'] = df['close'].pct_change().rolling(window=60, min_periods=30).std() * np.sqrt(60)

    df['volume_ma_20'] = df['vol'].rolling(window=20, min_periods=10).mean()
    df['volume_ratio'] = df['vol'] / df['volume_ma_20']

    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal']

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))

    df['bb_middle'] = df['ma_20']
    bb_std = df['close'].rolling(window=20, min_periods=10).std()
    df['bb_upper'] = df['bb_middle'] + 2 * bb_std
    df['bb_lower'] = df['bb_middle'] - 2 * bb_std
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['bb_breakout'] = np.where(df['close'] > df['bb_upper'], 1, np.where(df['close'] < df['bb_lower'], -1, 0))

    if 'net_mf_amount' in df.columns:
        df['net_mf_amount_ma_5'] = df['net_mf_amount'].rolling(window=5, min_periods=3).mean()
        df['net_mf_amount_ma_20'] = df['net_mf_amount'].rolling(window=20, min_periods=10).mean()

    # --- 周线KDJ金叉死叉信号 ---
    weekly_kdj_signal = 'None'
    weekly_k_latest, weekly_d_latest, weekly_j_latest = None, None, None
    
    if ts_code and df_weekly is not None and not df_weekly.empty:
        latest_weekly = df_weekly.tail(1)
        if not latest_weekly.empty:
            weekly_kdj_signal = latest_weekly['kdj_cross'].iloc[0]
            weekly_k_latest = latest_weekly['k'].iloc[0]
            weekly_d_latest = latest_weekly['d'].iloc[0]
            weekly_j_latest = latest_weekly['j'].iloc[0]
    
    df['weekly_kdj_signal'] = weekly_kdj_signal
    df['weekly_k_latest'] = weekly_k_latest
    df['weekly_d_latest'] = weekly_d_latest
    df['weekly_j_latest'] = weekly_j_latest

    indicator_cols = [
        'trade_date', 'close', 'volume_ratio', 'macd_hist', 'rsi_14', 
        'bb_width', 'bb_breakout', 'net_mf_amount_ma_5',
        'weekly_kdj_signal', 'weekly_k_latest', 'weekly_d_latest', 'weekly_j_latest'
    ]
    final_cols = [col for col in indicator_cols if col in df.columns]
    indicators_df = df[final_cols].tail(60)
    
    return indicators_df.to_json(orient='records', date_format='iso', force_ascii=False)

# --- 主数据加载函数 ---

def load_stock_data(ts_code):
    """
    通过API加载指定股票的所有相关数据。
    不再依赖本地文件，直接从Tushare获取。
    """
    if not pro:
        return None, "Tushare Pro接口未初始化，无法获取数据。"

    print(f"开始为 {ts_code} 从API获取数据...")
    
    # 1. 定义时间范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    
    # 2. 获取各类数据
    basic_df = get_basic_info(ts_code)
    quotes_df = get_quotes(ts_code, start_date, end_date)
    fundamentals_df = get_fundamentals(ts_code, start_date, end_date)
    moneyflows_df = get_moneyflow(ts_code, start_date, end_date)
    income_df = get_income(ts_code).tail(8)
    weekly_df_raw = get_weekly_data(ts_code)
    factors_df = get_factors_data(ts_code)

    # 检查关键数据是否获取成功
    if quotes_df.empty:
        return None, f"无法获取 {ts_code} 的核心行情数据，分析中止。"
    if basic_df.empty:
        return None, f"无法获取 {ts_code} 的公司基本信息，分析中止。"

    # 3. 数据处理与指标计算
    weekly_df_kdj = calculate_weekly_kdj(weekly_df_raw)
    technical_indicators_json = calculate_technical_indicators(quotes_df, moneyflows_df, weekly_df_kdj, ts_code)
    professional_analysis = analyze_professional_indicators(factors_df)

    # 4. 组装最终数据
    data = {
        'basic': basic_df.to_json(orient='records', date_format='iso', force_ascii=False),
        'quotes': quotes_df.to_json(orient='records', date_format='iso', force_ascii=False),
        'fundamentals': fundamentals_df.to_json(orient='records', date_format='iso', force_ascii=False),
        'moneyflows': moneyflows_df.to_json(orient='records', date_format='iso', force_ascii=False),
        'income': income_df.to_json(orient='records', date_format='iso', force_ascii=False),
        'technical_indicators': technical_indicators_json,
        'professional_indicators_analysis': professional_analysis
    }
    
    print(f"已成功为 {ts_code} 从API加载并处理完所有数据。")
    
    return data, None