import os
import pandas as pd
import re
import pdfkit
import shutil
from datetime import datetime
import requests
import subprocess

# --- Constants ---
CACHE_PATH = os.path.join(os.path.dirname(__file__), "cache")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "pdf_reports")
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_NAME = "SourceHanSansSC"
FONT_FILE_REGULAR = f"{FONT_NAME}-Regular.otf"
FONT_FILE_BOLD = f"{FONT_NAME}-Bold.otf"
FONT_PATH_REGULAR = os.path.join(FONT_DIR, FONT_FILE_REGULAR)
FONT_PATH_BOLD = os.path.join(FONT_DIR, FONT_FILE_BOLD)

# --- Helper Functions ---

def ensure_directories():
    """确保缓存、输出和字体目录存在"""
    os.makedirs(CACHE_PATH, exist_ok=True)
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    os.makedirs(FONT_DIR, exist_ok=True)

def check_wkhtmltopdf():
    """检查系统中是否安装了 wkhtmltopdf"""
    if shutil.which("wkhtmltopdf"):
        print("✅ wkhtmltopdf 已安装。")
        return True
    else:
        print("❌ 错误: 未在系统中找到 wkhtmltopdf。")
        print("请访问 https://wkhtmltopdf.org/downloads.html 下载并安装。")
        print("安装后，请确保将其可执行文件路径添加到系统的 PATH 环境变量中。")
        return False

def download_font_if_not_exists():
    """检查并下载字体文件"""
    if os.path.exists(FONT_PATH_REGULAR) and os.path.exists(FONT_PATH_BOLD):
        return True, "字体文件已存在。"

    font_urls = {
        FONT_FILE_REGULAR: "https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SourceHanSansSC-Regular.otf",
        FONT_FILE_BOLD: "https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SourceHanSansSC-Bold.otf"
    }

    for font_file, url in font_urls.items():
        font_path = os.path.join(FONT_DIR, font_file)
        if not os.path.exists(font_path):
            try:
                print(f"正在下载字体 {font_file}...")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(font_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"字体 {font_file} 下载成功。")
            except requests.exceptions.RequestException as e:
                error_message = f"下载字体 {font_file} 失败: {e}"
                print(error_message)
                if os.path.exists(font_path):
                    os.remove(font_path)
                return False, error_message
    
    return True, "字体文件下载并准备就绪。"

def markdown_to_html(markdown_text, ts_code, metadata):
    """
    将Markdown文本转换为包含内联CSS的HTML字符串。
    """
    # 解析Markdown内容
    lines = markdown_text.split('\n')
    html_body = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "综合分析报告" in line:
            continue
            
        if line.startswith('###'):
            html_body += f"<h3>{line.replace('###', '').strip()}</h3>\n"
        elif line.startswith('##'):
            html_body += f"<h2>{line.replace('##', '').strip()}</h2>\n"
        elif line.startswith('#'):
            continue
        
        elif line.startswith('* ') or line.startswith('- '):
            bullet_text = re.sub(r'^[\*\-]\s*', '', line)
            bullet_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', bullet_text)
            html_body += f"<li>{bullet_text}</li>\n"
        
        elif line and not line.startswith('---') and "免责声明" not in line:
            paragraph = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            if paragraph.strip():
                html_body += f"<p>{paragraph}</p>\n"

    # 报告元数据
    report_time = datetime.fromisoformat(metadata['timestamp']).strftime("%Y年%m月%d日 %H:%M")
    meta_info = f"""
    <div class="meta-info">
        <p><strong>报告生成时间:</strong> {report_time}</p>
        <p><strong>分析模型:</strong> {metadata['llm_provider']} ({metadata['llm_model']})</p>
    </div>
    """

    # 免责声明
    disclaimer = """
    <div class="disclaimer">
        <h2>⚠️ 重要声明</h2>
        <p>1. 本报告仅基于历史数据和公开信息由AI生成，不构成任何投资建议。</p>
        <p>2. 投资者应独立决策，自行承担投资风险。</p>
        <p>3. 市场有风险，投资需谨慎。</p>
    </div>
    """

    # 构建完整的HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>股票分析报告: {ts_code}</title>
        <style>
            @font-face {{
                font-family: '{FONT_NAME}';
                src: url('file:///{FONT_PATH_REGULAR.replace(os.sep, '/')}') format('opentype');
                font-weight: normal;
                font-style: normal;
            }}
            @font-face {{
                font-family: '{FONT_NAME}';
                src: url('file:///{FONT_PATH_BOLD.replace(os.sep, '/')}') format('opentype');
                font-weight: bold;
                font-style: normal;
            }}
            body {{
                font-family: '{FONT_NAME}', sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 20px;
            }}
            h1, h2, h3 {{
                font-weight: bold;
                color: #1a237e;
                border-bottom: 2px solid #c5cae9;
                padding-bottom: 5px;
            }}
            h1 {{ font-size: 24px; }}
            h2 {{ font-size: 20px; margin-top: 25px; }}
            h3 {{ font-size: 16px; margin-top: 20px; }}
            p {{ margin: 10px 0; }}
            li {{ margin-bottom: 5px; }}
            strong {{ color: #d84315; }}
            .meta-info {{
                background-color: #e8eaf6;
                border-left: 5px solid #3f51b5;
                padding: 10px;
                margin-bottom: 20px;
                font-size: 12px;
            }}
            .disclaimer {{
                margin-top: 30px;
                padding: 10px;
                border-top: 1px solid #ccc;
                font-size: 12px;
                color: #555;
            }}
        </style>
    </head>
    <body>
        <h1>📈 A股智能分析师报告: {ts_code}</h1>
        {meta_info}
        {html_body}
        {disclaimer}
    </body>
    </html>
    """
    return html_content

def find_latest_cache_file(ts_code=None):
    """
    查找最新的缓存文件。
    """
    ensure_directories()
    files = [os.path.join(CACHE_PATH, f) for f in os.listdir(CACHE_PATH) if f.endswith('.csv')]
    if ts_code:
        files = [f for f in files if os.path.basename(f).startswith(f"{ts_code}_")]
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def convert_cache_to_pdf(cache_filepath):
    """
    将指定的缓存CSV文件通过wkhtmltopdf转换为PDF。
    
    Returns:
        tuple: (success: bool, message: str, pdf_filepath: str or None)
    """
    if not cache_filepath or not os.path.exists(cache_filepath):
        error_msg = f"错误: 缓存文件不存在: {cache_filepath}"
        print(error_msg)
        return False, error_msg, None

    try:
        df = pd.read_csv(cache_filepath, encoding='utf-8-sig')
        if df.empty:
            error_msg = f"错误: 缓存文件为空: {cache_filepath}"
            print(error_msg)
            return False, error_msg, None
            
        analysis_content = df.iloc[0]['analysis_content']
        metadata = df.iloc[0].to_dict()
        ts_code = metadata.get('ts_code', 'UNKNOWN')

        print(f"正在为 {ts_code} 生成HTML内容...")
        html_string = markdown_to_html(analysis_content, ts_code, metadata)
        
        # 生成PDF文件名
        date_str = metadata.get('file_date', datetime.now().strftime('%Y%m%d'))
        time_str = metadata.get('file_time', datetime.now().strftime('%H%M%S'))
        pdf_filename = f"股票分析报告_{ts_code}_{date_str}_{time_str}.pdf"
        pdf_filepath = os.path.join(OUTPUT_PATH, pdf_filename)
        
        # 使用pdfkit生成PDF
        print(f"正在调用wkhtmltopdf生成PDF: {pdf_filename}...")
        options = {
            'encoding': "UTF-8",
            'custom-header': [
                ('Accept-Encoding', 'gzip')
            ],
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'enable-local-file-access': None
        }
        pdfkit.from_string(html_string, pdf_filepath, options=options)
        
        success_msg = f"✅ 报告已成功保存到: {pdf_filepath}"
        print(success_msg)
        return True, success_msg, pdf_filepath

    except FileNotFoundError:
        error_msg = "❌ 转换失败: 'wkhtmltopdf' command not found. 请确保已安装wkhtmltopdf并将其添加到系统PATH。"
        print(error_msg)
        return False, error_msg, None
    except Exception as e:
        # 捕获pdfkit的OSError，通常是因为wkhtmltopdf执行出错
        if "No wkhtmltopdf executable found" in str(e) or "Command failed" in str(e):
             error_msg = f"❌ 转换失败: wkhtmltopdf执行出错。请确保其已正确安装并配置。错误详情: {e}"
             print(error_msg)
             return False, error_msg, None
        else:
             error_msg = f"❌ 转换失败: {e}"
             print(error_msg)
             return False, error_msg, None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="将股票分析缓存文件转换为PDF报告。")
    parser.add_argument(
        "ts_code", 
        nargs='?', 
        default=None,
        help="要转换的股票代码 (e.g., 000001.SZ)。如果未提供，则转换最新的缓存文件。"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="直接指定要转换的缓存文件路径。"
    )
    
    args = parser.parse_args()
    
    # 1. 检查wkhtmltopdf
    if not check_wkhtmltopdf():
        exit(1)
        
    # 2. 检查字体
    ensure_directories()
    font_ready, msg = download_font_if_not_exists()
    if not font_ready:
        print(f"错误: {msg}")
        exit(1)

    # 3. 查找文件并转换
    if args.file:
        target_file = args.file
    else:
        print(f"正在查找 {'股票 ' + args.ts_code if args.ts_code else '最新'} 的缓存文件...")
        target_file = find_latest_cache_file(args.ts_code)

    if target_file:
        print(f"找到目标文件: {target_file}")
        success, message, pdf_path = convert_cache_to_pdf(target_file)
        if not success:
            print(message)
            exit(1)
    else:
        print("错误: 找不到匹配的缓存文件。")
