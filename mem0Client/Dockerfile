# Web界面Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 安装本地streamlit_chat_prompt组件
RUN pip install -e ./streamlit_chat_prompt

# 创建必要的目录
RUN mkdir -p data logs

# 设置环境变量
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8503
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 暴露端口
EXPOSE 8503

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8503/ || exit 1

# 启动命令
CMD ["streamlit", "run", "web_app_full_cn.py", "--server.port=8503", "--server.address=0.0.0.0", "--server.headless=true"]
