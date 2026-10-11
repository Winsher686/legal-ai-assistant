"""应用配置：统一从环境变量读取，支持 .env 覆盖。

所有敏感信息（LLM Key、数据库密码等）均通过环境变量注入，
避免硬编码到代码中。服务器部署时只需配置 .env 即可，无需改代码。
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置对象。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # 应用基础
    # ------------------------------------------------------------------
    APP_NAME: str = "企业法务知识库与法规制度智能问答系统"
    APP_ENV: str = "development"  # development / production / test
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ------------------------------------------------------------------
    # Mock 降级模式
    # ------------------------------------------------------------------
    # 当本地/CI 环境没有 Milvus/Neo4j/LLM 时，置为 true 可使用内存向量库、
    # 内存图数据库和假 LLM，端到端跑通逻辑。服务器生产环境请置为 false。
    USE_MOCK: bool = False

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    LLM_PROVIDER: str = "openai"  # openai / deepseek / qwen / mock
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""  # DeepSeek: https://api.deepseek.com ; Qwen(DashScope): https://dashscope.aliyuncs.com/compatible-mode/v1
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.2

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------
    EMBEDDING_PROVIDER: str = "bge"  # bge / openai / mock
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""

    # ------------------------------------------------------------------
    # Reranker（cross-encoder 精排）
    # ------------------------------------------------------------------
    RERANKER_MODEL: str = "BAAI/bge-reranker-large"

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "legal"
    POSTGRES_PASSWORD: str = "legal123"
    POSTGRES_DB: str = "legal_ai"
    # 完整连接串，缺省时按上述字段拼装
    POSTGRES_URL: str = ""

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    # ------------------------------------------------------------------
    # Milvus
    # ------------------------------------------------------------------
    MILVUS_HOST: str = "milvus"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "legal_knowledge_base"

    # ------------------------------------------------------------------
    # Neo4j
    # ------------------------------------------------------------------
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "legal123456"

    # ------------------------------------------------------------------
    # 存储目录
    # ------------------------------------------------------------------
    STORAGE_DIR: str = "/app/storage"
    DOCUMENT_DIR: str = "/app/storage/documents"

    # ------------------------------------------------------------------
    # RAG 检索参数
    # ------------------------------------------------------------------
    RAG_TOP_K: int = 20          # 召回候选数量
    RAG_FINAL_TOP_K: int = 5     # 送入 LLM 的最终数量
    RAG_RRF_K: int = 60          # RRF 融合常数
    CHUNK_SIZE: int = 800        # 切片最大字符数
    CHUNK_OVERLAP: int = 100     # 切片重叠字符数

    # ------------------------------------------------------------------
    # 限流
    # ------------------------------------------------------------------
    RATE_LIMIT_MAX_REQUESTS: int = 60      # 每窗口最大请求数
    RATE_LIMIT_WINDOW_SECONDS: int = 60    # 限流窗口（秒）

    # ------------------------------------------------------------------
    # 派生属性
    # ------------------------------------------------------------------
    @property
    def postgres_url(self) -> str:
        if self.POSTGRES_URL:
            return self.POSTGRES_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
