#!/bin/sh
# 后端容器启动脚本：等待数据库就绪后启动 uvicorn
set -e

echo "[entrypoint] waiting for PostgreSQL..."
python - <<'PY'
import time, os
import psycopg2
host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
user = os.getenv("POSTGRES_USER", "legal")
pwd  = os.getenv("POSTGRES_PASSWORD", "legal123")
db   = os.getenv("POSTGRES_DB", "legal_ai")
for _ in range(60):
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=db)
        conn.close()
        print("[entrypoint] PostgreSQL is ready")
        break
    except Exception as e:
        time.sleep(2)
else:
    print("[entrypoint] PostgreSQL not ready, continue anyway")
PY

# 初始化数据库表
python -m app.database.init_db || echo "[entrypoint] init_db skipped"

exec "$@"
