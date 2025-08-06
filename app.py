import streamlit as st
import re
import os
from datetime import datetime
from agent import StockAnalystAgent
from llm_services import LLM_PROVIDERS
from cache_manager import get_cached_files, load_cached_analysis
import config
from converter import convert_cache_to_pdf, check_wkhtmltopdf, download_font_if_not_exists, ensure_directories

# --- Streamlit UI ---
st.set_page_config(page_title="A股智能分析师 Agent", layout="wide", initial_sidebar_state="expanded")

st.title("📈 A股智能分析师 Agent (Demo)")
st.markdown("由多个LLM和 Streamlit 强力驱动")

# 初始化Agent
# 使用st.cache_resource来避免每次重跑都初始化，提高性能
@st.cache_resource
def get_agent():
    return StockAnalystAgent()

agent = get_agent()

# --- UI ---
st.sidebar.header("分析设置")

# 缓存管理功能
st.sidebar.subheader("📂 缓存管理")

# 获取所有缓存文件
cached_files = get_cached_files()

if cached_files:
    # 默认选项（不加载）
    cache_options = ["--- 不加载缓存 ---"] + [file_info['display_name'] for file_info in cached_files]
    
    selected_cache = st.sidebar.selectbox(
        "选择要加载的缓存报告",
        options=cache_options,
        help="选择之前生成的分析报告进行查看"
    )
    
    # 处理缓存加载
    if selected_cache != "--- 不加载缓存 ---":
        # 找到对应的缓存文件
        selected_file_info = None
        for file_info in cached_files:
            if file_info['display_name'] == selected_cache:
                selected_file_info = file_info
                break
        
        if selected_file_info:
            # 加载缓存的分析报告
            cached_analysis, metadata = load_cached_analysis(selected_file_info['filepath'])
            
            if cached_analysis:
                # 将缓存的分析结果加载到session state
                st.session_state.last_analysis = cached_analysis
                st.session_state.last_ts_code = metadata['ts_code']
                st.session_state.cached_metadata = metadata
                
                # 显示缓存文件信息
                st.sidebar.info(f"""
                **缓存报告信息**
                - 股票代码: {metadata['ts_code']}
                - 生成时间: {metadata.get('timestamp', '未知')[:19]}
                - 使用模型: {metadata.get('llm_provider', '未知')} ({metadata.get('llm_model', '未知')})
                """)
            else:
                st.sidebar.error(f"加载缓存失败: {metadata}")
    
    # 显示缓存统计
    st.sidebar.write(f"共有 {len(cached_files)} 个缓存报告")
    
    # 提供清理缓存的选项
    if st.sidebar.button("🗑️ 清理所有缓存", help="删除所有缓存的分析报告"):
        try:
            for file_info in cached_files:
                os.remove(file_info['filepath'])
            st.sidebar.success("所有缓存已清理！")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"清理缓存失败: {e}")
else:
    st.sidebar.info("暂无缓存报告")

st.sidebar.markdown("---")

# LLM选择
st.sidebar.subheader("LLM 选择")
selected_provider = st.sidebar.selectbox(
    "选择LLM提供商",
    options=list(LLM_PROVIDERS.keys())
)

provider_models = LLM_PROVIDERS[selected_provider]["models"]
selected_model = st.sidebar.selectbox(
    "选择模型",
    options=provider_models,
    index=provider_models.index(LLM_PROVIDERS[selected_provider]["default_model"])
)

# 股票代码输入
st.sidebar.subheader("股票输入")
ts_code_input = st.sidebar.text_input(
    "请输入A股股票代码", 
    value="000001.SZ",
    help="格式示例: '000001.SZ' (平安银行), '600519.SH' (贵州茅台)"
)

analyze_button = st.sidebar.button("🤖 开始分析", type="primary")

st.sidebar.subheader("报告导出")

# 检查PDF转换环境
pdf_ready = False
try:
    if check_wkhtmltopdf():
        ensure_directories()
        font_ready, font_msg = download_font_if_not_exists()
        if font_ready:
            pdf_ready = True
            st.sidebar.success("✅ PDF转换环境就绪")
        else:
            st.sidebar.warning(f"⚠️ 字体下载失败: {font_msg}")
    else:
        st.sidebar.error("❌ 请先安装 wkhtmltopdf")
except Exception as e:
    st.sidebar.error(f"❌ PDF环境检查失败: {e}")

# PDF导出功能
if cached_files and pdf_ready:
    st.sidebar.write("选择要导出为PDF的报告:")
    
    # 创建一个选择框来选择要导出的报告
    export_options = ["--- 选择报告 ---"] + [file_info['display_name'] for file_info in cached_files]
    
    selected_export = st.sidebar.selectbox(
        "选择报告",
        options=export_options,
        key="export_select",
        help="选择要转换为PDF的报告"
    )
    
    if selected_export != "--- 选择报告 ---":
        # 找到对应的缓存文件
        selected_export_file = None
        for file_info in cached_files:
            if file_info['display_name'] == selected_export:
                selected_export_file = file_info
                break
        
        if selected_export_file:
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("📄 转换为PDF", key="convert_pdf"):
                    with st.spinner("正在生成PDF..."):
                        try:
                            success, message, pdf_path = convert_cache_to_pdf(selected_export_file['filepath'])
                            if success:
                                st.sidebar.success("✅ PDF转换成功！")
                                if pdf_path:
                                    pdf_filename = os.path.basename(pdf_path)
                                    st.sidebar.info(f"PDF文件: {pdf_filename}")
                                    st.sidebar.info("已保存到 pdf_reports 目录")
                            else:
                                st.sidebar.error(f"❌ PDF转换失败: {message}")
                        except Exception as e:
                            st.sidebar.error(f"❌ PDF转换失败: {e}")
            
            with col2:
                # 显示文件信息
                file_size_mb = selected_export_file['file_size'] / (1024 * 1024)
                st.sidebar.write(f"大小: {file_size_mb:.2f}MB")

# 显示已生成的PDF文件
pdf_reports_dir = os.path.join(os.path.dirname(__file__), "pdf_reports")
if os.path.exists(pdf_reports_dir):
    pdf_files = [f for f in os.listdir(pdf_reports_dir) if f.endswith('.pdf')]
    if pdf_files:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📁 已生成的PDF报告")
        
        # 按修改时间排序
        pdf_files_with_time = []
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_reports_dir, pdf_file)
            mtime = os.path.getmtime(pdf_path)
            file_size = os.path.getsize(pdf_path)
            pdf_files_with_time.append((pdf_file, mtime, file_size))
        
        pdf_files_with_time.sort(key=lambda x: x[1], reverse=True)
        
        st.sidebar.write(f"共有 {len(pdf_files)} 个PDF文件")
        
        # 添加打开PDF目录按钮
        if st.sidebar.button("📂 打开PDF目录", help="在文件管理器中打开PDF报告目录"):
            import subprocess
            try:
                # Windows
                subprocess.run(['explorer', pdf_reports_dir], check=True)
            except:
                st.sidebar.error("无法打开目录")
        
        # 显示最新的几个PDF文件
        with st.sidebar.expander(f"查看最新的PDF文件 (显示{min(5, len(pdf_files))}个)", expanded=False):
            for i, (pdf_file, mtime, file_size) in enumerate(pdf_files_with_time[:5]):
                file_time = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
                file_size_mb = file_size / (1024 * 1024)
                
                # 提取股票代码（如果文件名格式正确）
                try:
                    parts = pdf_file.split('_')
                    if len(parts) >= 2:
                        stock_code = parts[1]  # 股票分析报告_{股票代码}_...
                        st.write(f"**{stock_code}** - {file_time}")
                    else:
                        st.write(f"**{pdf_file[:25]}...** - {file_time}")
                except:
                    st.write(f"**{pdf_file[:25]}...** - {file_time}")
                
                st.caption(f"大小: {file_size_mb:.1f}MB")
                st.markdown("---")
            
            if len(pdf_files) > 5:
                st.write(f"💡 还有 {len(pdf_files) - 5} 个PDF文件...")
    else:
        st.sidebar.info("📁 PDF目录为空")

elif not pdf_ready:
    st.sidebar.info("PDF转换功能需要安装 wkhtmltopdf")
else:
    st.sidebar.info("暂无可导出的报告")

st.subheader("AI 分析报告")

# 显示缓存信息（如果有的话）
if st.session_state.get('cached_metadata'):
    metadata = st.session_state.cached_metadata
    st.info(f"📋 当前显示的是缓存报告 - 生成时间: {metadata.get('timestamp', '未知')[:19]}")

# 使用会话状态来保存上一次的分析结果
if 'last_analysis' not in st.session_state:
    st.session_state.last_analysis = ""
if 'last_ts_code' not in st.session_state:
    st.session_state.last_ts_code = ""

if analyze_button:
    # 清除缓存状态（因为这是新的分析）
    if 'cached_metadata' in st.session_state:
        del st.session_state.cached_metadata
    
    # 校验输入格式
    if not re.match(r'^\d{6}\.(SH|SZ)$', ts_code_input.strip()):
        st.error("请输入有效的股票代码格式，例如 '000001.SZ' 或 '600519.SH'")
    else:
        with st.spinner(f"正在使用 {selected_provider} ({selected_model}) 分析股票 {ts_code_input}..."):
            analysis_result = agent.analyze_stock(
                ts_code_input.strip(),
                llm_provider=selected_provider,
                llm_model=selected_model
            )
            st.session_state.last_analysis = analysis_result
            st.session_state.last_ts_code = ts_code_input.strip()
            
            # 显示分析结果
            st.markdown(st.session_state.last_analysis)
            
            # 在报告结束后添加PDF导出按钮
            if pdf_ready:
                st.markdown("---")
                st.subheader("📄 报告导出")
                
                col_pdf1, col_pdf2 = st.columns([1, 3])
                with col_pdf1:
                    if st.button("📄 导出当前报告为PDF", key="export_new_report_pdf"):
                        # 获取最新生成的缓存文件
                        ts_code = ts_code_input.strip()
                        cached_files = get_cached_files(ts_code)  # 获取该股票的缓存文件
                        if cached_files:
                            # 获取最新的缓存文件
                            latest_cache_file = cached_files[0]  # 已按时间倒序排列
                            with st.spinner("正在生成PDF..."):
                                try:
                                    success, message, pdf_path = convert_cache_to_pdf(latest_cache_file['filepath'])
                                    if success:
                                        st.success("✅ PDF转换成功！")
                                        if pdf_path:
                                            pdf_filename = os.path.basename(pdf_path)
                                            st.info(f"PDF文件已保存: {pdf_filename}")
                                    else:
                                        st.error(f"❌ PDF转换失败: {message}")
                                except Exception as e:
                                    st.error(f"❌ PDF转换失败: {e}")
                        else:
                            st.error("找不到对应的分析报告缓存文件")
                
                with col_pdf2:
                    st.info("💡 PDF文件将保存到 pdf_reports 目录中，您可以在侧边栏的PDF管理区域查看和管理所有生成的PDF文件。")
            
            # 分析完成后刷新页面以更新sidebar缓存列表
            # 注意：这会导致页面重新加载，所以放在最后
            st.rerun()
else:
    # 默认显示或显示上一次的分析结果
    if st.session_state.last_analysis:
        st.markdown(st.session_state.last_analysis)
        
        # 在报告结束后添加PDF导出按钮
        if pdf_ready and (st.session_state.get('cached_metadata') or st.session_state.get('last_ts_code')):
            st.markdown("---")
            st.subheader("📄 报告导出")
            
            col_pdf1, col_pdf2 = st.columns([1, 3])
            with col_pdf1:
                if st.button("📄 导出当前报告为PDF", key="export_current_report_pdf"):
                    # 如果是缓存报告
                    if st.session_state.get('cached_metadata'):
                        metadata = st.session_state.cached_metadata
                        # 找到对应的缓存文件
                        current_cache_file = None
                        cached_files = get_cached_files()  # 重新获取缓存文件列表
                        for file_info in cached_files:
                            if (file_info['ts_code'] == metadata['ts_code'] and 
                                file_info['date'] == metadata['file_date'] and 
                                file_info['time'] == metadata['file_time']):
                                current_cache_file = file_info
                                break
                        
                        if current_cache_file:
                            with st.spinner("正在生成PDF..."):
                                try:
                                    success, message, pdf_path = convert_cache_to_pdf(current_cache_file['filepath'])
                                    if success:
                                        st.success("✅ PDF转换成功！")
                                        if pdf_path:
                                            pdf_filename = os.path.basename(pdf_path)
                                            st.info(f"PDF文件已保存: {pdf_filename}")
                                    else:
                                        st.error(f"❌ PDF转换失败: {message}")
                                except Exception as e:
                                    st.error(f"❌ PDF转换失败: {e}")
                        else:
                            st.error("找不到对应的缓存文件")
                    
                    # 如果是新生成的报告，需要找到最新的缓存文件
                    elif st.session_state.get('last_ts_code'):
                        ts_code = st.session_state.last_ts_code
                        cached_files = get_cached_files(ts_code)  # 获取该股票的缓存文件
                        if cached_files:
                            # 获取最新的缓存文件
                            latest_cache_file = cached_files[0]  # 已按时间倒序排列
                            with st.spinner("正在生成PDF..."):
                                try:
                                    success, message, pdf_path = convert_cache_to_pdf(latest_cache_file['filepath'])
                                    if success:
                                        st.success("✅ PDF转换成功！")
                                        if pdf_path:
                                            pdf_filename = os.path.basename(pdf_path)
                                            st.info(f"PDF文件已保存: {pdf_filename}")
                                    else:
                                        st.error(f"❌ PDF转换失败: {message}")
                                except Exception as e:
                                    st.error(f"❌ PDF转换失败: {e}")
                        else:
                            st.error("找不到对应的分析报告缓存文件")
            
            with col_pdf2:
                st.info("💡 PDF文件将保存到 pdf_reports 目录中，您可以在侧边栏的PDF管理区域查看和管理所有生成的PDF文件。")
    else:
        st.info("请在左侧输入股票代码并点击'开始分析'按钮，以获取AI生成的分析报告。")
