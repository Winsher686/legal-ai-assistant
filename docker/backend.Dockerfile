# ---------- 后端服务镜像 ----------
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（pymupdf / psycopg2 等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装依赖（利用 docker layer cache）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY app ./app

# 存储目录
RUN mkdir -p /app/storage/documents

EXPOSE 8000

# 默认启动 API；worker 使用同名镜像，通过 command 覆盖
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
