# 使用官方的 Python 镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制字体和 requirements.txt 到容器中
COPY fonts/ /app/fonts/
COPY requirements.txt .

# 安装 wkhtmltopdf
RUN apt-get update && \
    apt-get install -y wkhtmltopdf && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码到容器中
COPY . .

# 暴露 Streamlit 端口
EXPOSE 8501

# 设置 Streamlit 健康检查
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 运行 Streamlit 应用
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
